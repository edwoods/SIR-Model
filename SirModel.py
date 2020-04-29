import numpy as np
import math
from enum import IntEnum
from PyQt5 import QtCore, QtWidgets


def GetValue(text):
    value = float(text)
    if value.is_integer():
        value = int(value)

    return value

class Cols(IntEnum):   # cols of the SirModel data array
    group,\
    status,\
    dayInfec,\
    nStrgrs,\
    serviceGuy,\
    xPos,\
    yPos,\
    isolated,\
    nInfected,\
    lastDataCol = range(10)

class Ctrls(IntEnum):
    nPeeps, \
    minDaysSick, \
    pRecover, pDie, \
    pInfectOwn, pInfectStgr, \
    nInOwnGrp, \
    nStrgrsPerDay, StrangeRng, \
    pServiceGuy, SrvNStgrPerDay, SrvStgrRange, \
    pContactTrace, nTracePerDay, \
    LastCtrl = range(15)

    # SIPthres, SIPnStgr, SIPstrgrRng, SIPpInfectOwn, SIPpInfectStgr, SIPpObey, SIPduration, \

    @classmethod
    def GetDefaults(cls):
        cs = np.zeros(cls.LastCtrl)
        cs[cls.nPeeps] = 5000
        cs[cls.minDaysSick] = 10
        cs[cls.pRecover] = 0.54
        cs[cls.pDie] = 0.04
        cs[cls.pInfectStgr] = 0.05
        cs[cls.pInfectOwn] = 0.2
        cs[cls.nInOwnGrp] = 3
        cs[cls.nStrgrsPerDay] = 5
        cs[cls.StrangeRng] = 20
        cs[cls.pServiceGuy] = 0.05
        cs[cls.SrvNStgrPerDay] = 10
        cs[cls.SrvStgrRange] = 30
        cs[cls.pContactTrace] = 0.10
        cs[cls.nTracePerDay] = 10

        return cs


class SirModel:
    def __init__(self, cntrlsIn):
        self.cs = []
        self.sipEndDay = 0
        self.SipStartDays = 0
        self.SipEndDays = 0
        self.infected = 0
        self.groups = 0
        self.serviceGuys = 0
        self.nonServiceGuys = 0
        self.infectionRate = 0
        self.counts = np.zeros((1000, 5))
        self.Controls = cntrlsIn
        self.SetCntrls()
        self.newInfected = 0
        self.nRecoveredOrDead = 0
        c = int(Cols.lastDataCol)

        self.data = np.zeros((self.cs[Ctrls.nPeeps], Cols.lastDataCol))
        self.Reset()

    def SetCntrls(self):
        self.cs.clear()
        for i, ctrl in enumerate(self.Controls):
            line:QtWidgets.QLineEdit = ctrl
            text = line.text()
            value = GetValue(text)

            self.cs.append(value)

    def InfectedToRecovered(self, day):
        infected = np.nonzero(self.data[:, Cols.status] == 11)[0]
        longSickGuys = infected[day - self.data[infected, Cols.dayInfec] > self.cs[Ctrls.minDaysSick]]

        if longSickGuys.size == 0:
            return

        urand = np.random.sample(len(longSickGuys))
        died = longSickGuys[self.cs[Ctrls.pDie] > urand]
        self.data[died, Cols.status] = 99
        infected = np.nonzero(self.data[:, Cols.status] == 11)

        gonners = np.nonzero((day - self.data[infected, Cols.dayInfec]) > 20)[0]
        self.data[gonners, Cols.status] = 99

        urand2 = np.random.sample(len(longSickGuys))

        # recovers = longSickGuys(S.cs(Ctrls.pRecover) > randDraw);

        recovers = longSickGuys[self.cs[Ctrls.pRecover] > urand2]
        self.data[recovers, Cols.status] = 22

        self.nRecoveredOrDead = np.count_nonzero(recovers) + np.count_nonzero(died) + np.count_nonzero(gonners)

    def SpreadInfection(self, day):
        infected = np.nonzero(self.data[:, Cols.status] == 11)
        self.newInfected = 0
        if infected[0].size == 0:
            return

        for ii in np.nditer(infected):
            closeAss = np.array(self.groups[int(self.data[ii, Cols.group])])
            suscepts = closeAss[self.data[closeAss, Cols.status] == 0]
            urand = np.random.sample(len(suscepts))
            newSickClose = suscepts[urand < self.cs[Ctrls.pInfectOwn]]

            self.data[newSickClose, Cols.dayInfec] = day
            self.data[newSickClose, Cols.status] = 11

            #  generate and check strangers
            farthestStranger = self.cs[Ctrls.StrangeRng]
            nstrangers = self.cs[Ctrls.nStrgrsPerDay]
            if self.data[ii, Cols.serviceGuy]:
                farthestStranger = self.cs[Ctrls.SrvStgrRange]
                nstrangers = self.cs[Ctrls.SrvNStgrPerDay]

            belowStart = max(0, closeAss[0] - farthestStranger)
            belowEnd = max(0, closeAss[0])
            aboveStart = min(closeAss[-1] + 1, self.cs[Ctrls.nPeeps] - 1)
            aboveEnd = min(closeAss[-1] + 1 + farthestStranger, self.cs[Ctrls.nPeeps] - 1)
            strangers = np.r_[np.arange(belowStart, belowEnd), np.arange(aboveStart, aboveEnd)]
            index = range(len(strangers))
            sgIndex = np.random.permutation(index)
            sgIndex = sgIndex[0:nstrangers]
            strangers = strangers[sgIndex]

            suscepts2 = strangers[self.data[strangers, Cols.status] == 0]
            urand2 = np.random.sample(len(suscepts2))
            newSickStgr = suscepts2[urand2 < self.cs[Ctrls.pInfectStgr]]

            newII = len(newSickClose) + len(newSickStgr)
            self.newInfected = self.newInfected + newII

            self.data[ii, Cols.nInfected] = self.data[ii, Cols.nInfected] + newII
            self.data[newSickStgr, Cols.dayInfec] = day
            self.data[newSickStgr, Cols.status] = 11

    def Reset(self):
        self.SetCntrls()
        self.sipEndDay = 999999
        self.counts = np.zeros((1000, 5))  # 1000 days, 4 type of counts
        self.data = np.zeros((self.cs[Ctrls.nPeeps], Cols.lastDataCol))
        nPeeps2 = math.ceil(self.cs[Ctrls.nPeeps] / 2)
        self.infected = [nPeeps2, nPeeps2 + 10]
        self.newInfected = 0

        self.data[self.infected, Cols.status] = 11
        self.data[self.infected, Cols.dayInfec] = 0

        nextPeep = 0
        ngrp = 0
        self.groups = []

        while True:
            npeep = np.random.poisson(self.cs[Ctrls.nInOwnGrp]) + 1
            lastPeep = min(self.cs[Ctrls.nPeeps], nextPeep + npeep)
            peeps = [n for n in range(nextPeep, lastPeep)]
            self.groups.append(peeps)
            self.data[peeps, Cols.group] = ngrp

            ngrp += 1
            nextPeep += npeep
            if nextPeep > self.cs[Ctrls.nPeeps]:
                break

        everyone = [n for n in range(self.cs[Ctrls.nPeeps])]

        sgIndex = np.random.permutation(everyone)
        self.serviceGuys = sgIndex[0: math.floor(self.cs[Ctrls.nPeeps] * self.cs[Ctrls.pServiceGuy])]

        nStrangers = np.random.poisson(self.cs[Ctrls.nInOwnGrp], len(self.serviceGuys)) + 1  # ServNstgrs = avg number of peeps per day
        self.data[self.serviceGuys, Cols.nStrgrs] = nStrangers
        self.data[self.serviceGuys, Cols.serviceGuy] = 1

         # nonServiceGuys guys, the general public
        self.nonServiceGuys = np.nonzero(self.data[:, Cols.serviceGuy] == 0)
        nStrangers = np.random.poisson(self.cs[Ctrls.nStrgrsPerDay], len(self.nonServiceGuys)) + 1  # nStrangers = avg number of peeps per day
        self.data[self.nonServiceGuys, Cols.nStrgrs] = nStrangers

        width = 11
        hgt = 3
        nCols = round((math.sqrt(self.cs[Ctrls.nPeeps] /hgt / width) * width))
        nRows = math.ceil(self.cs[Ctrls.nPeeps] / nCols)

        self.data[:, Cols.xPos] = np.mod(everyone, nCols)
        self.data[:, Cols.yPos] = np.floor(np.divide(everyone, nCols))
