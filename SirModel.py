import numpy as np
import math
from enum import IntEnum
from PyQt5 import QtWidgets


def GetValue(text):
    try:
        value = float(text)
        if value.is_integer():
            value = int(value)
    except:
        return None

    return value


class CountType(IntEnum):  # cols of the SirModel data array
    infected, \
    newInfected, \
    dead, \
    recovered, \
    nonInfected, \
    lastCountType = range(6)

class StatusType(IntEnum):
    nonInfected = 0
    infected = 11
    recovered = 22
    dead = 99


class Cols(IntEnum):  # cols of the SirModel data array
    family, \
    status, \
    dayInfec, \
    serviceGuy, \
    xPos, \
    yPos, \
    symptomatic, \
    isolated, \
    nInfected, \
    lastDataCol = range(10)


class Ctrls(IntEnum):
    nPeeps, \
    minDaysSick, \
    pRecover, pDie, \
    pInfectFamily, pInfectFriend, pInfectStgr, \
    nInFamily, nFriends, FriendsPerDay, FriendRadius, \
    StgrsPerDay, StrangerRadius, \
    pServiceGuy, ServStgrPerDay, ServStgrRadius, \
    DaysTillSymptoms, pShowSymptoms, pTest, nTestsPerDay,\
    LastCtrl = range(21)

    # SIPthres, SIPnStgr, SIPstrgrRng, SIPpInfectOwn, SIPpInfectStgr, SIPpObey, SIPduration, \

    @classmethod
    def GetDefaults(cls):
        cs = np.zeros(cls.LastCtrl)
        cs[cls.nPeeps] = 2000
        cs[cls.minDaysSick] = 10

        cs[cls.pRecover] = 0.54
        cs[cls.pDie] = 0.04

        cs[cls.pInfectFamily] = 0.05
        cs[cls.pInfectFriend] = 0.02
        cs[cls.pInfectStgr] = 0.01

        cs[cls.nInFamily] = 3

        cs[cls.nFriends] = 10
        cs[cls.FriendsPerDay] = 1
        cs[cls.FriendRadius] = 30

        cs[cls.StgrsPerDay] = 1
        cs[cls.StrangerRadius] = 50

        cs[cls.pServiceGuy] = 0.05
        cs[cls.ServStgrPerDay] = 10
        cs[cls.ServStgrRadius] = 30

        cs[cls.DaysTillSymptoms] = 5
        cs[cls.pShowSymptoms] = 0.75  # https://www.nbcnews.com/
        cs[cls.pTest] = 0.30
        cs[cls.nTestsPerDay] = 20

        return cs


class SirModel:
    def __init__(self, cntrlsIn):
        self.cs = []
        self.sipEndDay = 0
        self.SipStartDays = 0
        self.SipEndDays = 0
        self.infected = 0
        self.family = 0
        self.friends = 0
        self.serviceGuys = 0
        self.nonServiceGuys = 0
        self.infectionRate = 0
        self.counts = np.zeros((1000, CountType.lastCountType))
        self.Controls = cntrlsIn
        self.SetCntrls()
        self.newInfected = 0
        self.nRecoveredOrDead = 0
        self.contacts = []
        self.everyone = []

        self.data = np.zeros((self.cs[Ctrls.nPeeps], Cols.lastDataCol))
        self.Reset()

    def SetCntrls(self):
        self.cs.clear()
        for i, ctrl in enumerate(self.Controls):
            line: QtWidgets.QLineEdit = ctrl
            text = line.text()
            value = GetValue(text)

            self.cs.append(value)

    def InfectedToRecovered(self, day):
        infected = np.nonzero(self.data[:, Cols.status] == StatusType.infected)[0]
        longSickGuys = infected[day - self.data[infected, Cols.dayInfec] > self.cs[Ctrls.minDaysSick]]

        if longSickGuys.size == 0:
            return

        urand = np.random.sample(len(longSickGuys))
        died = longSickGuys[self.cs[Ctrls.pDie] > urand]
        self.data[died, Cols.status] = 99
        infected = np.nonzero(self.data[:, Cols.status] == StatusType.infected)

        gonners = np.nonzero((day - self.data[infected, Cols.dayInfec]) > 20)[0]
        self.data[gonners, Cols.status] = 99

        urand2 = np.random.sample(len(longSickGuys))

        # recovers = longSickGuys(S.cs(Ctrls.pRecover) > randDraw);

        recovers = longSickGuys[self.cs[Ctrls.pRecover] > urand2]
        self.data[recovers, Cols.status] = 22

        self.nRecoveredOrDead = np.count_nonzero(recovers) + np.count_nonzero(died) + np.count_nonzero(gonners)

    def Testing(self, day):
        # you get a test if
        #   - you are infected
        #   - for at least DaysTillSymptoms show
        #   - you show symptoms
        #   - you are are not isolated

        # find guys that have been infected a while
        symptomatic = np.logical_and(
            self.data[:, Cols.status] == StatusType.infected,
            (day - self.data[:, Cols.dayInfec]) > self.cs[Ctrls.DaysTillSymptoms])

        # limit to the guys that will show symptoms
        symptomatic = np.logical_and(
            symptomatic, self.data[:, Cols.symptomatic] == 1)

        # limit to guys who are not isolated
        symptomatic = np.logical_and(
            symptomatic, self.data[:, Cols.isolated] == 0)

        symptomatic = self.everyone[symptomatic]  # get the guys

        if len(symptomatic) == 0:
            return

        symptomatic = np.random.permutation(symptomatic)

        nTests = min(self.cs[Ctrls.nTestsPerDay], math.ceil(self.cs[Ctrls.pTest] * len(symptomatic)))
        testies = symptomatic[:int(nTests)]

        self.data[testies, Cols.isolated] = 1
        pass

    def SpreadInfection(self, day):
        self.newInfected = 0
        infected = np.logical_and(
            self.data[:, Cols.status] == StatusType.infected,
            self.data[:, Cols.isolated] == 0)

        infected = self.everyone[infected]
        if len(infected) == 0:
            return

        for ii in np.nditer(infected):
            # infect family
            family = np.array(self.family[int(self.data[ii, Cols.family])])
            suscepts = family[self.data[family, Cols.status] == 0]
            urand = np.random.sample(len(suscepts))
            newSickFamily = suscepts[urand < self.cs[Ctrls.pInfectFamily]]

            self.data[newSickFamily, Cols.dayInfec] = day
            self.data[newSickFamily, Cols.status] = StatusType.infected
            self.contacts[ii].extend(newSickFamily.tolist())
            # for n in newSickFamily:
            #    self.contacts[n].append(ii)

            # infect friends
            nFriendsToday = np.random.poisson(self.cs[Ctrls.FriendsPerDay])
            # nFriendsToday = self.cs[Ctrls.FriendsPerDay]
            friends1 = self.friends[ii]
            friends = np.random.permutation(friends1)
            friends = friends[:nFriendsToday]

            susceptsFriends = friends[self.data[friends, Cols.status] == 0]
            urand = np.random.sample(len(susceptsFriends))
            newSickFriends = susceptsFriends[urand < self.cs[Ctrls.pInfectFriend]]

            self.data[newSickFriends, Cols.dayInfec] = day
            self.data[newSickFriends, Cols.status] = StatusType.infected
            self.contacts[ii].extend(newSickFriends.tolist())
            # for n in newSickFriends:
            #     self.contacts[n].append(ii)

            #  generate and check strangers
            farthestStranger = self.cs[Ctrls.StrangerRadius]
            nstrangers = self.cs[Ctrls.StgrsPerDay]
            if self.data[ii, Cols.serviceGuy]:
                farthestStranger = self.cs[Ctrls.ServStgrRadius]
                nstrangers = self.cs[Ctrls.ServStgrPerDay]

            nstrangersP = nstrangers
            belowStart = max(0, ii - farthestStranger)
            aboveEnd = min(ii + farthestStranger, self.cs[Ctrls.nPeeps] - 1)
            strangers = np.arange(belowStart, aboveEnd)    # everyone inside StrangerRadius
            strangers = np.setdiff1d(strangers, family)    # remove family members
            strangers = np.setdiff1d(strangers, friends1)  # remove friends
            strangers = np.random.permutation(strangers)
            strangers = strangers[:nstrangers]

            suscepts2 = strangers[self.data[strangers, Cols.status] == 0]
            urand2 = np.random.sample(len(suscepts2))
            newSickStgr = suscepts2[urand2 < self.cs[Ctrls.pInfectStgr]]
            self.contacts[ii].extend(newSickStgr.tolist())
            # for n in newSickStgr:
            #     self.contacts[n].append(ii)

            newII = len(newSickFamily) + len(newSickFriends) + len(newSickStgr)
            self.newInfected = self.newInfected + newII

            self.data[ii, Cols.nInfected] = self.data[ii, Cols.nInfected] + newII
            self.data[newSickStgr, Cols.dayInfec] = day
            self.data[newSickStgr, Cols.status] = StatusType.infected

        self.totalInfected += self.newInfected

    def Reset(self):
        self.SetCntrls()

        self.everyone = np.arange(self.cs[Ctrls.nPeeps])

        self.contacts = [[] for i in range(self.cs[Ctrls.nPeeps])]
        self.sipEndDay = 999999
        self.counts = np.zeros((1000, CountType.lastCountType))  # 1000 days, 5 type of counts
        self.data = np.zeros((self.cs[Ctrls.nPeeps], Cols.lastDataCol))

        # self.infected = [nPeeps2, nPeeps2 + 10]
        #  INITIAL infected guys
        infected = list(range(1000, self.cs[Ctrls.nPeeps], 1000))

        self.newInfected = 0
        self.totalInfected = len(infected)

        self.data[infected, Cols.status] = StatusType.infected
        self.data[infected, Cols.dayInfec] = 0

        # create the families: i.e. list of adjacent people
        nextPeep = 0
        ngrp = 0
        self.family = []

        while True:
            npeep = np.random.poisson(self.cs[Ctrls.nInFamily]) + 1
            lastPeep = min(self.cs[Ctrls.nPeeps], nextPeep + npeep)
            peeps = [n for n in range(nextPeep, lastPeep)]
            self.family.append(peeps)
            self.data[peeps, Cols.family] = ngrp

            ngrp += 1
            nextPeep += npeep
            if nextPeep > self.cs[Ctrls.nPeeps]:
                break

        # create the friends: i.e. list of people you see frequently
        self.friends = [0]*self.cs[Ctrls.nPeeps]

        for i in range(self.cs[Ctrls.nPeeps]):
            belowStart = max(0, i - self.cs[Ctrls.FriendRadius])
            # belowEnd = max(0, i -  self.cs[Ctrls.nInFamily])
            # aboveStart = min(self.cs[Ctrls.nPeeps]-1, i + self.cs[Ctrls.nInFamily])
            aboveEnd = min(self.cs[Ctrls.nPeeps]-1, i + self.cs[Ctrls.FriendRadius])
            friends = np.arange(belowStart, aboveEnd)
            family = self.family[int(self.data[i, Cols.family])]
            friends = np.setdiff1d(friends, family)
            friends = np.random.permutation(friends)
            self.friends[i] = friends[:self.cs[Ctrls.nFriends]]

        #  pick the guys who will show symptoms
        symptomatics = np.random.permutation(self.everyone)
        symptomatics = symptomatics[:math.floor(self.cs[Ctrls.nPeeps] * self.cs[Ctrls.pShowSymptoms])]
        self.data[symptomatics, Cols.symptomatic] = 1

        #  pick the guys who work in service industry
        self.serviceGuys = np.random.permutation(self.everyone)
        self.serviceGuys = self.serviceGuys[:math.floor(self.cs[Ctrls.nPeeps] * self.cs[Ctrls.pServiceGuy])]
        self.data[self.serviceGuys, Cols.serviceGuy] = 1

        # nonServiceGuys guys, the general public
        self.nonServiceGuys = np.nonzero(self.data[:, Cols.serviceGuy] == 0)

        width = 11
        hgt = 3
        nCols = round((math.sqrt(self.cs[Ctrls.nPeeps] / hgt / width) * width))
        nRows = math.ceil(self.cs[Ctrls.nPeeps] / nCols)

        self.data[:, Cols.xPos] = np.mod(self.everyone, nCols)
        self.data[:, Cols.yPos] = np.floor(np.divide(self.everyone, nCols))

