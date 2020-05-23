from typing import Any, List

import numpy as np
import math
from enum import IntEnum
from PyQt5 import QtWidgets

# Python program to illustrate union
# Without repetition
def Union(lst1, lst2):
    final_list = list(set(lst1) | set(lst2))
    return final_list


def GetValue(text):
    try:
        value = float(text)
        if value.is_integer():
            value = int(value)
    except:
        return None

    return value


class CountType(IntEnum):  # cols of the SirModel data array
    [infected,
     isoBySymptom,
     isoByWatch,
     dead,
     infectRatio,
     lastCountType] = range(6)


class StatusType(IntEnum):  # status in SirModel.data[:,status]
    nonInfected = 0
    infected = 11
    recovered = 22
    dead = 99
    byWatch = 30
    bySymptom = 31


class StatType(IntEnum):  # index into RunStats
    [infected,
     nonIsolated,
     isoBySymptom,
     isoByWatch,
     removed,
     lastRunStat] = range(6)


class Cols(IntEnum):  # cols of the SirModel data array
    [family,
     status,
     dayInfec,
     serviceGuy,
     hasWatch,
     needTest,
     xPos,
     yPos,
     symptomatic,
     isolatedOn,
     isolatedBy,   # 31 = symptoms -> test;  30 = by watch
     lastDataCol] = range(12)


class Ctrls(IntEnum):
    [nPeeps,
     minDaysSick,
     pRecover, pDie,
     pInfectFamily, pInfectFriend, pInfectStgr,
     nInFamily, nFriends, FriendsPerDay, FriendRadius,
     StgrsPerDay, StrangerRadius,
     pServiceGuy, ServStgrPerDay, ServStgrRadius,
     DaysTillSymptoms, pShowSymptoms, pTest, nTestsPerDay,
     pHaveWatch, Test2Isolate,
     LastCtrl] = range(23)

    # SIPthres, SIPnStgr, SIPstrgrRng, SIPpInfectOwn, SIPpInfectStgr, SIPpObey, SIPduration, \

    @classmethod
    def GetDefaults(cls):
        cs = np.zeros(cls.LastCtrl)
        cs[cls.nPeeps] = 20000
        cs[cls.minDaysSick] = 10

        cs[cls.pRecover] = 0.54
        cs[cls.pDie] = 0.04

        cs[cls.pInfectFamily] = 0.05
        cs[cls.pInfectFriend] = 0.02
        cs[cls.pInfectStgr] = 0.02

        cs[cls.nInFamily] = 3

        cs[cls.nFriends] = 10
        cs[cls.FriendsPerDay] = 2
        cs[cls.FriendRadius] = 30

        cs[cls.StgrsPerDay] = 3
        cs[cls.StrangerRadius] = 50

        cs[cls.pServiceGuy] = 0.05
        cs[cls.ServStgrPerDay] = 10
        cs[cls.ServStgrRadius] = 30

        cs[cls.DaysTillSymptoms] = 5
        cs[cls.pShowSymptoms] = 0.75  # https://www.nbcnews.com/
        cs[cls.pTest] = 0.90
        cs[cls.nTestsPerDay] = 2000
        cs[cls.pHaveWatch] = 0.001
        cs[cls.Test2Isolate] = 2

        return cs

class PeepType:
    def __init__(self):
        self.friends = 0
        self.family = 0
        self.contacts = 0
        self.id = 0

    def SetFamily(self, id, familyMembers):
        self.id = id
        self.family = familyMembers

    def MakeFriends(self, controls):
        belowStart = max(0, self.id -  controls[Ctrls.FriendRadius])
        aboveEnd = min(controls[Ctrls.nPeeps] - 1, self.id + controls[Ctrls.FriendRadius])
        self.friends = np.arange(belowStart, aboveEnd)
        self.friends = np.setdiff1d(self.friends, self.family)
        self.friends = np.random.permutation(self.friends)
        self.friends = self.friends[:controls[Ctrls.nFriends]]
        self.friends = np.sort(self.friends)


class SirModel:
    EndOfTime = 999999

    maxSamples = 20
    maxSampleDay = 500

    def __init__(self, cntrlsIn):
        self.SceneTitle = 'Relaxed SIP'
        self.cs = []
        self.sipEndDay = 0
        self.SipStartDays = 0
        self.SipEndDays = 0
        self.TotalInfected = 0
        self.serviceGuys = 0
        self.nonServiceGuys = 0
        self.Controls = cntrlsIn
        self.SetCntrls()
        self.newInfected = 0
        self.nRecoveredOrDead = 0
        self.everyone = []
        self.Peeps = []  # type: list[PeepType]

        self.ctrlsChanged = False
        self.Sample = -1
        self.RunStats = np.zeros([StatType.lastRunStat, self.maxSamples, self.maxSampleDay])  # 3 types of stats, 20 samples, 150 days
        self.ResetStats = False

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

        self.RunStats[StatType.removed,
                      self.Sample,
                      day] = self.nRecoveredOrDead

    def CheckWatch(self, day):
        # find newly infected guys with a watch
        watchGuys = self.everyone[self.cs[:,Cols.hasWatch] == 1]

        pass

    def DailySummary(self, day):

        infected = self.everyone[self.data[:, Cols.status] == StatusType.infected]
        isolated = infected[self.data[infected, Cols.isolatedOn] < day]

        # nIsoBySymp = isolated[self.data[isolated, Cols.isolatedBy] == StatusType.bySymptom]
        # nIsoByWatch = isolated[self.data[isolated, Cols.isolatedBy] == StatusType.byWatch]

        nInfected = len(infected)
        # nIsoBySymp = len(nIsoBySymp)
        # nIsoByWatch = len(nIsoByWatch)

        nUnawareInfected = nInfected - len(isolated)
        self.RunStats[StatType.nonIsolated,
                      self.Sample,
                      day] = nUnawareInfected

        # self.RunStats[self.infectedRS,
        #               self.Sample,
        #               day] = nInfected
        #
        # self.RunStats[self.isoBySymptom,
        #               self.Sample,
        #               day] = nIsoBySymp
        #
        # self.RunStats[self.isoByWatch,
        #               self.Sample,
        #               day] = nIsoByWatch

    def Testing(self, day):
        # you get a test if
        #   - your watch says you need a test
        #   - you are infected
        #   - for at least DaysTillSymptoms show
        #   - you show symptoms
        #   - you are are not isolated

        # find guys that have been infected
        symptomatic = self.everyone[self.data[:, Cols.status] == StatusType.infected]

        #  for at least DaysTillSymptoms
        symptomatic = symptomatic[(day - self.data[symptomatic, Cols.dayInfec]) > self.cs[Ctrls.DaysTillSymptoms]]

        # limit to the guys that will show symptoms
        symptomatic = symptomatic[self.data[symptomatic, Cols.symptomatic] == 1]

        # limit the guys that have NOT been tested recently
        symptomatic = symptomatic[self.data[symptomatic, Cols.isolatedOn] == self.EndOfTime]

        #  combine the 2 list of guys to be tested
        # needTest = np.union1d(needTest, symptomatic)
        isolated = symptomatic

        if len(symptomatic) != 0:
            #  only get to test a certain % a day
            nTests = min(self.cs[Ctrls.nTestsPerDay], math.ceil(self.cs[Ctrls.pTest] * len(symptomatic)))

            gotTest = np.random.permutation(symptomatic)
            gotTest = gotTest[:int(nTests)]

            # some tested people may not be sick: these will test negative. Isolate only the infected
            isolated = gotTest[self.data[gotTest, Cols.status] == StatusType.infected]

            # mark the guys that get tested to be isolated later: in Test2Isolate days
            self.data[isolated, Cols.isolatedBy] = StatusType.bySymptom
            self.data[isolated, Cols.isolatedOn] = day + self.cs[Ctrls.Test2Isolate]

        # get the guys that the watch alerted to get tested
        alertedByWatch = self.everyone[self.data[:, Cols.needTest] != 0]
        if len(alertedByWatch) != 0:
            x= self.data[alertedByWatch,:]

        self.data[alertedByWatch, Cols.isolatedBy] = StatusType.byWatch
        self.data[alertedByWatch, Cols.isolatedOn] = day  # isolate the day after you are infected

        self.RunStats[StatType.isoByWatch,
                      self.Sample,
                      day] = len(alertedByWatch)

        # print('day ', day, ' alertedByWatch: ', alertedByWatch)

        #  combine the 2 list of guys to be tested
        needTest = np.union1d(alertedByWatch, isolated)

        if len(needTest) > 0:
            # print('top ', needTest)

            for ii in needTest:
                # contacts of this guy
                contacts = self.Peeps[ii].contacts
                self.data[contacts, Cols.needTest] += 1
                # print('day ', day, ' contacts: ', ii, contacts)

                self.Peeps[ii].contacts = []  # guy ii's contacts have been warned

            # reset the needTest flag
            self.data[needTest, Cols.needTest] = 0

        isolated = self.everyone[self.data[:, Cols.status] == StatusType.infected]
        # print('day ', day, ' total isolated: ', isolated, ' on ', self.data[isolated, Cols.isolatedOn])
        x = 0

    def InfectFamily(self, ii, day):
        family = self.Peeps[ii].family
        suscepts = family[self.data[family, Cols.status] == 0]
        urand = np.random.sample(len(suscepts))
        newSickFamily = suscepts[urand < self.cs[Ctrls.pInfectFamily]]

        self.data[newSickFamily, Cols.dayInfec] = day
        self.data[newSickFamily, Cols.status] = StatusType.infected

        if self.data[ii, Cols.hasWatch]:
            self.Peeps[ii].contacts = Union(self.Peeps[ii].contacts, newSickFamily)

        return newSickFamily

    def InfectFriends(self, ii, day):
        nFriendsToday = np.random.poisson(self.cs[Ctrls.FriendsPerDay])
        friends = np.random.permutation(self.Peeps[ii].friends)
        friends = friends[:nFriendsToday]

        susceptsFriends = friends[self.data[friends, Cols.status] == 0]
        urand = np.random.sample(len(susceptsFriends))
        newSickFriends = susceptsFriends[urand < self.cs[Ctrls.pInfectFriend]]

        self.data[newSickFriends, Cols.dayInfec] = day
        self.data[newSickFriends, Cols.status] = StatusType.infected

        if self.data[ii, Cols.hasWatch]:
            self.Peeps[ii].contacts = Union(self.Peeps[ii].contacts, newSickFriends)

        return newSickFriends

    def GetStrangers(self,ii):
        farthestStranger = self.cs[Ctrls.StrangerRadius]
        nstrangers = self.cs[Ctrls.StgrsPerDay]
        if self.data[ii, Cols.serviceGuy]:
            farthestStranger = self.cs[Ctrls.ServStgrRadius]
            nstrangers = self.cs[Ctrls.ServStgrPerDay]

        belowStart = max(0, ii - farthestStranger)
        belowEnd = max(0, self.Peeps[ii].family[0])
        aboveStart = min(self.Peeps[ii].family[-1] + 1, self.cs[Ctrls.nPeeps] - 1)
        aboveEnd = min(ii + farthestStranger, self.cs[Ctrls.nPeeps] - 1)
        strangers = np.append(np.arange(belowStart, belowEnd),
                              np.arange(aboveStart, aboveEnd))

        strangers = np.random.permutation(strangers)
        # grab nstrangers from the stranger list
        stgrs = np.arange(nstrangers)
        nFound = 0
        friendSet = set(self.Peeps[ii].friends)
        for istgr in strangers:
            if istgr not in friendSet:
                stgrs[nFound] = istgr
                nFound += 1
                if nFound == nstrangers:
                    break

        return stgrs

    def SpreadInfection(self, day):
        self.newInfected = 0

        infected = self.everyone[self.data[:, Cols.status] == StatusType.infected]
        infected = infected[self.data[infected, Cols.isolatedOn] > day]  # and not isolated

        # print('day ', day, ' inf ! iso: ', infected, ' on ', self.data[infected, Cols.isolatedOn])

        if len(infected) == 0:
            return

        for ii in np.nditer(infected):
            # infect family
            newSickFamily = self.InfectFamily(ii, day)

            # infect friends
            newSickFriends = self.InfectFriends(ii, day)

            # infect strangers
            strangers = self.GetStrangers(ii)

            suscepts2 = strangers[self.data[strangers, Cols.status] == 0]
            urand2 = np.random.sample(len(suscepts2))
            newSickStgr = suscepts2[urand2 < self.cs[Ctrls.pInfectStgr]]

            if self.data[ii, Cols.hasWatch]:
                self.Peeps[ii].contacts = Union(self.Peeps[ii].contacts, newSickStgr)

            newII = len(newSickFamily) + len(newSickFriends) + len(newSickStgr)
            self.newInfected = self.newInfected + newII

            self.data[newSickStgr, Cols.dayInfec] = day
            self.data[newSickStgr, Cols.status] = StatusType.infected

        self.RunStats[StatType.infected,
                      self.Sample,
                      day] = self.newInfected

        self.TotalInfected += self.newInfected

    def Reset(self):
        if self.ResetStats:    # user clicked or max num samples reached
            self.ResetStats = False
            self.Sample = -1
            self.RunStats.fill(0)  # 3 types of stats, 20 samples, 150 days

        # if self.ctrlsChanged:
        #     self.ctrlsChanged = False
        #     self.Sample = -1
        #     #  save the stats
        #     np.savetxt("RunStats.csv", self.RunStats, delimiter=",")
        #     self.RunStats.fill(0)

        self.Sample += 1
        self.SetCntrls()

        self.everyone = np.arange(self.cs[Ctrls.nPeeps])

        self.sipEndDay = self.EndOfTime
        self.data = np.zeros((self.cs[Ctrls.nPeeps], Cols.lastDataCol))

        #  INITIAL infected guys
        infected = list(range(1000, self.cs[Ctrls.nPeeps], 1000))

        self.RunStats[StatType.infected,
                      self.Sample,
                      0] = len(infected)

        self.TotalInfected = len(infected)

        self.newInfected = 0

        self.data[infected, Cols.status] = StatusType.infected
        self.data[infected, Cols.dayInfec] = 0

        # create the families: i.e. list of adjacent people
        self.Peeps = [0] * self.cs[Ctrls.nPeeps]
        nextPeep = 0
        while True:
            npeep = np.random.poisson(self.cs[Ctrls.nInFamily]) + 1
            lastPeep = min(self.cs[Ctrls.nPeeps], nextPeep + npeep)
            family = np.arange(nextPeep, lastPeep)
            for id in family:
                self.Peeps[id] = PeepType()
                self.Peeps[id].SetFamily(id, family)
                self.Peeps[id].MakeFriends(self.cs)
                self.Peeps[id].contacts = []

            nextPeep += npeep
            if nextPeep > self.cs[Ctrls.nPeeps]:
                break

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

        # set the isolate day to a big number
        self.data[:, Cols.isolatedOn] = self.EndOfTime

        # guys with a watch
        watchers = np.random.permutation(self.everyone)
        nWatches = math.floor(self.cs[Ctrls.pHaveWatch] * self.cs[Ctrls.nPeeps])
        watchers = watchers[: nWatches]
        self.data[watchers, Cols.hasWatch] = 1

        width = 11
        hgt = 3
        nCols = round((math.sqrt(self.cs[Ctrls.nPeeps] / hgt / width) * width))
        nRows = math.ceil(self.cs[Ctrls.nPeeps] / nCols)

        self.data[:, Cols.xPos] = np.mod(self.everyone, nCols)
        self.data[:, Cols.yPos] = np.floor(np.divide(self.everyone, nCols))
