import matplotlib
import numpy as np
from PyQt5.QtWidgets import qApp
import os, csv

from ControlsWindow import ControlsWindow, SceneStatus
from SirModel import SirModel, Cols, Ctrls, GetValue, CountType, StatusType

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, \
    NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5 import QtCore, QtGui, QtWidgets

matplotlib.use('Qt5Agg')


def make_format(current, other):
    # current and other are axes
    def format_coord(x, y):
        # x, y are data coordinates
        # convert to display coords
        display_coord = current.transData.transform((x, y))
        inv = other.transData.inverted()
        # convert back to data coords with respect to ax
        ax_coord = inv.transform(display_coord)
        coords = [ax_coord, (x, y)]
        return ('Left: {:<40}    Right: {:<}'
                .format(*['({:.3f}, {:.3f})'.format(x, y) for x, y in coords]))

    return format_coord


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.resize(900, 660)
        self.cntrls = []
        self.newPlot = True

        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.setWindowTitle("SIR Model")

        # menus file: open, save, quit   view: controls
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.setMenuBar(self.menubar)

        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setTitle("File")
        self.menubar.addAction(self.menuFile.menuAction())

        self.actionSave = QtWidgets.QAction(parent=self, text="Save")
        self.menuFile.addAction(self.actionSave)
        self.actionSave.triggered.connect(self.SaveFile)

        self.menuFile.addSeparator()

        self.actionQuit = QtWidgets.QAction(parent=self, text="Quit")
        self.actionQuit.setShortcut('Ctrl+Q')
        self.actionQuit.triggered.connect(qApp.quit)
        self.menuFile.addAction(self.actionQuit)

        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setTitle("View")
        self.menubar.addAction(self.menuView.menuAction())

        self.actionControls = QtWidgets.QAction(self)
        self.actionControls.setText("Controls")
        self.actionControls.triggered.connect(self.ShowControls)
        self.actionControls.setShortcut('Alt+C')
        self.menuView.addAction(self.actionControls)

        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout.setSpacing(3)

        self.CtrlsStatsLayout = QtWidgets.QVBoxLayout()
        self.CtrlsStatsLayout.setContentsMargins(-1, -1, 0, -1)
        self.horizontalLayout.addLayout(self.CtrlsStatsLayout)

        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setFrameShape(QtWidgets.QFrame.Box)
        self.splitter.setChildrenCollapsible(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.horizontalLayout.addWidget(self.splitter)

        self.SirParamsBox = QtWidgets.QGroupBox(self.centralwidget)
        self.SirParamsBox.setTitle("SIR Controls")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.SirParamsBox)
        self.horizontalLayout_6.setContentsMargins(2, 6, 2, 2)
        self.horizontalLayout_6.setSpacing(2)
        self.CtrlsStatsLayout.addWidget(self.SirParamsBox)

        self.SPLabelLayout = QtWidgets.QVBoxLayout()
        self.SPLabelLayout.setContentsMargins(0, 0, 2, 0)
        self.SPLabelLayout.setSpacing(0)
        self.horizontalLayout_6.addLayout(self.SPLabelLayout)

        self.SPeditsLayout = QtWidgets.QVBoxLayout()
        self.SPeditsLayout.setContentsMargins(0, 0, 0, 0)
        self.SPeditsLayout.setSpacing(0)
        self.horizontalLayout_6.addLayout(self.SPeditsLayout)

        self.AddParameters()

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.SPLabelLayout.addItem(spacerItem)

        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.SPeditsLayout.addItem(spacerItem1)

        self.SirStatsBox = QtWidgets.QGroupBox(self.centralwidget)
        self.SirStatsBox.setTitle("SIR Stats")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.SirStatsBox)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 4)
        self.CtrlsStatsLayout.addWidget(self.SirStatsBox)

        self.statsNames = QtWidgets.QLabel(self.SirStatsBox)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.statsNames.setFont(font)

        self.statsNames.setText("Day\n"
                                "n Susceptable\n"
                                "Total Infected\n"
                                "n Infected\n"
                                "n Recovered\n"
                                "n Dead\n"
                                "New Infected\n"
                                "New Recover/Died\n"
                                "Infection Rate")
        self.statsNames.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop | QtCore.Qt.AlignTrailing)
        self.statsNames.setIndent(0)
        self.horizontalLayout_5.addWidget(self.statsNames)

        self.StatsData = QtWidgets.QLabel(self.SirStatsBox)
        # font = QtGui.QFont()
        # font.setPointSize(10)
        self.StatsData.setFont(font)
        self.StatsData.setText("1\n10000\n0\n\0\n")
        self.StatsData.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.horizontalLayout_5.addWidget(self.StatsData)

        self.ButtonLayout = QtWidgets.QHBoxLayout()
        self.ButtonLayout.setContentsMargins(-1, 0, -1, -1)

        self.ResetButton = QtWidgets.QPushButton(self.centralwidget)
        self.ResetButton.setMaximumSize(QtCore.QSize(50, 16777215))
        self.ResetButton.setText("Reset")
        self.ResetButton.clicked.connect(self.ResetClicked)
        self.ButtonLayout.addWidget(self.ResetButton)

        self.NewPlot = QtWidgets.QPushButton(self.centralwidget)
        self.NewPlot.setMaximumSize(QtCore.QSize(50, 16777215))
        self.NewPlot.setText("NewPlot")
        self.NewPlot.clicked.connect(self.NewPlotClicked)
        self.ButtonLayout.addWidget(self.NewPlot)

        self.RunButton = QtWidgets.QPushButton(self.centralwidget)
        self.RunButton.setMaximumSize(QtCore.QSize(50, 16777215))
        self.RunButton.setText("Run")
        self.RunButton.clicked.connect(self.RunClicked)
        self.ButtonLayout.addWidget(self.RunButton)

        self.CtrlsStatsLayout.addLayout(self.ButtonLayout)
        self.horizontalLayout.addLayout(self.CtrlsStatsLayout)

        # add the plots
        self.TopPlotFrame = QtWidgets.QFrame(self.splitter)
        self.TopPlotFrame.setFrameShape(QtWidgets.QFrame.Box)
        self.TopPlotFrame.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.verticalLayout = QtWidgets.QVBoxLayout(self.TopPlotFrame)

        # scatter plot of people with color = status
        self.TPfigure = Figure()
        self.tpAx = self.TPfigure.add_subplot(111)
        self.Topcanvas = FigureCanvas(self.TPfigure)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.Topcanvas.setSizePolicy(sizePolicy)
        toolbar = NavigationToolbar(self.Topcanvas, self)

        self.verticalLayout.addWidget(toolbar)
        self.verticalLayout.addWidget(self.Topcanvas)

        x, y, s, c = np.random.rand(4, 20000)
        self.tpAx.scatter(x, y, 1, marker='.')

        # line plot of number of people vs day
        self.BottomPlotFrame = QtWidgets.QFrame(self.splitter)
        self.BottomPlotFrame.setFrameShape(QtWidgets.QFrame.Box)
        self.BottomPlotFrame.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.BottomPlotFrame)

        self.PvDfigure, self.PvDax = plt.subplots(constrained_layout=True)
        self.ax2 = self.PvDax.twinx()
        self.ax2.format_coord = make_format(self.ax2, self.PvDax)

        self.PvDcanvas = FigureCanvas(self.PvDfigure)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.PvDcanvas.setSizePolicy(sizePolicy)
        toolbar2 = NavigationToolbar(self.PvDcanvas, self)

        self.verticalLayout_2.addWidget(toolbar2)
        self.verticalLayout_2.addWidget(self.PvDcanvas)

        # x = np.linspace(0, 10)
        # self.PvDax.plot(x, np.sin(x) + x + np.random.randn(50))
        # self.PvDax.plot(x, np.sin(x) + 0.5 * x + np.random.randn(50))
        # self.PvDax.plot(x, np.sin(x) + 2 * x + np.random.randn(50))
        # self.PvDax.plot(x, np.sin(x) - 0.5 * x + np.random.randn(50))
        # self.PvDax.plot(x, np.sin(x) - 2 * x + np.random.randn(50))
        # self.PvDax.plot(x, np.sin(x) + np.random.randn(50))
        # self.PvDax.set_title("filler plot")

        self.playTimer = QtCore.QTimer()
        self.playTimer.setInterval(10)
        self.playTimer.timeout.connect(self.Run)

        self.running = False
        self.day = 0
        self.SirModel = SirModel(self.cntrls)
        self.ControlsWindow = ControlsWindow(self.cntrls, self.SirModel)

        QtCore.QMetaObject.connectSlotsByName(self)

    def RunClicked(self):
        if self.running:
            self.running = False
            self.playTimer.stop()
            self.RunButton.setText('Run')
        else:
            self.running = True
            self.playTimer.start()
            self.RunButton.setText('Pause')

    def ShowControls(self):
        self.ControlsWindow.show()  # Restore from systray
        self.ControlsWindow.raise_()

    def SaveFile(self):
        pass

    def ResetClicked(self):
        self.ControlsWindow.sceneStatus = SceneStatus.end
        self.day = 0
        self.SirModel.Reset()

        if not self.running:
            self.RunClicked()

    def NewPlotClicked(self):
        self.newPlot = True
        self.PvDax.cla()

        # self.running = False
        # self.playTimer.stop()

    def Run(self):
        if not self.running:
            return

        if self.day >= 1000:  # see: SirModel.Reset-- only save data for 1000 days
            self.RunClicked()
            return

        # check if there is a Scenario running
        if self.ControlsWindow.Scenario:
            if self.ControlsWindow.sceneStatus == SceneStatus.run:
                self.ControlsWindow.NextDay()

            elif self.ControlsWindow.sceneStatus == SceneStatus.end:
                self.ResetClicked()
                self.ControlsWindow.FirstDay()

        self.DrawStuff()

        if self.SirModel.counts[self.day, CountType.infected] == 0:  # the number of infected = 0
            self.ResetClicked()
            return

        self.day += 1
        self.SirModel.Testing(self.day)
        self.SirModel.InfectedToRecovered(self.day)
        self.SirModel.SpreadInfection(self.day)

    def AddParameters(self):

        ctrlNames = [str(Ctrls(x)) for x in range(Ctrls.LastCtrl)]
        ctrlVals = Ctrls.GetDefaults()

        for n in range(int(Ctrls.LastCtrl)):
            pName = ctrlNames[n].split('.')[1]  # e.g. pName = 'Cntrls.nPeeps' just need 'nPeeps'
            pVal = GetValue(ctrlVals[n])  # pVal of the nth Cntrl
            label = QtWidgets.QLabel(pName, self.SirParamsBox)
            label.setMinimumSize(QtCore.QSize(0, 18))
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            label.setSizePolicy(sizePolicy)

            label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
            self.SPLabelLayout.addWidget(label, 0, QtCore.Qt.AlignRight)

            lineEdit = QtWidgets.QLineEdit(self.SirParamsBox)
            lineEdit.setMinimumSize(QtCore.QSize(0, 18))
            lineEdit.setMaximumHeight(18)
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
            lineEdit.setSizePolicy(sizePolicy)
            lineEdit.setFixedWidth(80)
            lineEdit.setText(str(pVal))
            lineEdit.editingFinished.connect(lambda x=n: self.ControlChanged(x))

            self.cntrls.append(lineEdit)
            self.SPeditsLayout.addWidget(self.cntrls[n])

    def ControlChanged(self, n):
        oldValue = self.SirModel.cs[n]

        text = self.cntrls[n].text()
        newValue = GetValue(text)

        if newValue is None:
            self.cntrls[n].setText(str(oldValue))
            return

        if newValue != oldValue:
            self.SirModel.cs[n] = newValue

    def DrawStuff(self):
        x = self.SirModel.data[:, Cols.xPos]
        y = self.SirModel.data[:, Cols.yPos]

        # nonservice susceptables
        nsp = np.logical_and(self.SirModel.data[:, Cols.status] == StatusType.nonInfected, (self.SirModel.data[:, Cols.serviceGuy] == 0))

        # service susceptables
        ssp = np.logical_and(self.SirModel.data[:, Cols.status] == StatusType.nonInfected, (self.SirModel.data[:, Cols.serviceGuy] == 1))

        # nonservice infected
        nip = np.logical_and(self.SirModel.data[:, Cols.status] == StatusType.infected, self.SirModel.data[:, Cols.serviceGuy] == 0)

        # service infected
        sip = np.logical_and(self.SirModel.data[:, Cols.status] == StatusType.infected, self.SirModel.data[:, Cols.serviceGuy] == 1)

        # recovered
        ir = self.SirModel.data[:, Cols.status] == 22

        # dead
        id = self.SirModel.data[:, Cols.status] == 99

        # isolated
        iso = np.logical_and(self.SirModel.data[:, Cols.status] == StatusType.infected, self.SirModel.data[:, Cols.isolated] == 1)

        self.SirModel.counts[self.day, CountType.infected] = np.count_nonzero(nip) + np.count_nonzero(sip)  # infected
        self.SirModel.counts[self.day, CountType.newInfected] = self.SirModel.newInfected
        self.SirModel.counts[self.day, CountType.dead] = np.count_nonzero(id)  # dead
        self.SirModel.counts[self.day, CountType.nonInfected] = np.count_nonzero(nsp) + np.count_nonzero(ssp)  # suspectable
        self.SirModel.counts[self.day, CountType.recovered] = np.count_nonzero(ir)  # recovered

        if self.day % 10 == 0:
            self.tpAx.cla()
            self.tpAx.set_title("The entire population")
            # self.tpAx.scatter(x[nsp], y[nsp], s=12, color='b', marker='.', label='non service non infected')
            self.tpAx.scatter(x[ssp], y[ssp], s=18, color='b', marker='+')
            self.tpAx.scatter(x[nip], y[nip], s=4, color='r', marker='.')
            self.tpAx.scatter(x[sip], y[sip], color='r', marker='+')
            self.tpAx.scatter(x[ir], y[ir], s=4, color='g', marker='.')
            self.tpAx.scatter(x[id], y[id], color='k', marker='*')
            self.tpAx.scatter(x[iso], y[iso], color='y', marker='o')

            if self.newPlot:
                self.PvDax.cla()
                self.ax2.cla()
                self.PvDax.set_title("Counts of people vs Day")
                self.PvDax.set_xlabel('day')
                self.PvDax.set_ylabel('Number of Infected')

            days = np.arange(0, self.day + 1)

            colors = ['r', 'r', 'k', 'g', 'b']
            labels = ['<- infected', '<- new infected', '<- dead', 'recovered ->', 'non-infected']
            axes = [self.PvDax, self.PvDax, self.PvDax, self.ax2, self.ax2]
            width = ['1', '.5', '1', '.5', '.5']
            dash = [False, True, False, True, True]

            plots = [0] * 4
            for iplt in range(4):  # don't draw the number of non infected
                plots[iplt], = axes[iplt].plot(days, self.SirModel.counts[days, iplt], color=colors[iplt], linewidth=width[iplt])
                if dash[iplt]:
                    plots[iplt].set_dashes([6, 2])

            self.PvDax.legend(plots, labels, loc='best')

            self.newPlot = False
            self.PvDax.grid(True)

            self.Topcanvas.draw()
            self.PvDcanvas.draw()

        cnts = self.SirModel.counts[self.day, :].astype(int)

        stats = str(self.day) \
                + '\n' + str(cnts[CountType.nonInfected]) \
                + '\n' + str(self.SirModel.totalInfected) \
                + '\n' + str(cnts[CountType.infected]) \
                + '\n' + str(cnts[CountType.recovered]) \
                + '\n' + str(cnts[CountType.dead]) \
                + '\n' + str(self.SirModel.newInfected) \
                + '\n' + str(self.SirModel.nRecoveredOrDead)

        self.StatsData.setText(stats)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')

    app.setStyleSheet("QToolTip {\
     font-size:10pt;\
     color:white; padding:2px;\
     border-width:2px;\
     border-style:solid;\
     border-radius:20px;\
     background-color: black;\
     border: 1px solid white;\
     overflow:hidden;}");

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())
