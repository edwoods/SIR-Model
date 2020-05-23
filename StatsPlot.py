from PyQt5 import QtCore, QtWidgets, QtGui
import numpy as np

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from SirModel import Cols, Ctrls, StatType, StatusType


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, constrained_layout=True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class StatsPlot(QtWidgets.QWidget):
    def closeEvent(self, event):
        app = QtWidgets.QApplication.instance()
        app.closeAllWindows()

    def __init__(self, controls, SirModel, *args, **kwargs):
        super(StatsPlot, self).__init__(*args, **kwargs)

        self.controls = controls  # type: list[QtWidgets.QLineEdit]
        self.SirModel = SirModel

        self.NewWindow = False

        self.resize(860, 451)
        self.setWindowTitle("Multi-run stats")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self)
        self.horizontalLayout_2.setContentsMargins(1, 2, 1, 1)
        self.horizontalLayout_2.setSpacing(4)

        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setContentsMargins(4, -1, 1, -1)
        self.verticalLayout.setSpacing(2)

        self.groupBox_2 = QtWidgets.QGroupBox(self)
        self.groupBox_2.setTitle("SIR Controls")
        self.verticalLayout.addWidget(self.groupBox_2)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_3.setContentsMargins(2, 2, 1, 1)
        self.horizontalLayout_3.setSpacing(6)

        font = QtGui.QFont()
        font.setPointSize(10)

        self.ctrlNames = QtWidgets.QLabel(self.groupBox_2)
        self.ctrlNames.setText("names")
        self.ctrlNames.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop | QtCore.Qt.AlignTrailing)
        self.ctrlNames.setFont(font)

        self.AddControlNames()

        self.horizontalLayout_3.addWidget(self.ctrlNames)

        self.ctrlValues = QtWidgets.QLabel(self.groupBox_2)
        self.ctrlValues.setText("values")
        self.ctrlValues.setAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.ctrlValues.setFont(font)
        self.horizontalLayout_3.addWidget(self.ctrlValues)

        self.SaveButton = QtWidgets.QPushButton(self)
        self.SaveButton.setText("Save")
        self.SaveButton.clicked.connect(self.SaveWindow)
        self.verticalLayout.addWidget(self.SaveButton)
        self.horizontalLayout_2.addLayout(self.verticalLayout)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(2, 2, -1, -1)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        # self.canvas.axes.plot([0,1,2,3,4], [10,1,20,3,40])
        self.ax2 = self.canvas.axes.twinx()

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.setSizePolicy(sizePolicy)

        toolbar = NavigationToolbar(self.canvas, self)
        self.verticalLayout_2.addWidget(toolbar)
        self.verticalLayout_2.addWidget(self.canvas)

        x = np.linspace(0, 10)
        self.canvas.axes.plot(x, np.sin(x) + x + np.random.randn(50))
        self.canvas.axes.plot(x, np.sin(x) + 0.5 * x + np.random.randn(50))
        self.canvas.axes.plot(x, np.sin(x) + 2 * x + np.random.randn(50))
        self.canvas.axes.plot(x, np.sin(x) - 0.5 * x + np.random.randn(50))
        self.canvas.axes.plot(x, np.sin(x) - 2 * x + np.random.randn(50))
        self.canvas.axes.plot(x, np.sin(x) + np.random.randn(50))
        self.canvas.axes.set_title("filler plot")

        QtCore.QMetaObject.connectSlotsByName(self)

        # self.show()

    def SaveWindow(self):
        import datetime
        from pathlib import Path

        myPath = Path("./Plots")
        myPath.mkdir(parents=True, exist_ok=True)

        day = datetime.datetime.now()
        name = day.strftime('%y-%m-%d %H.%M.%S.png')

        title = self.windowTitle() + ' '
        name = './Plots/' + title + name
        self.grab().save(name)
        return

    def Update(self, day):
        self.setWindowTitle('Multi-run stats- ' + self.SirModel.SceneTitle)

        isolated = self.SirModel.everyone[self.SirModel.data[:, Cols.isolatedOn] == day]
        isoBySymptom = isolated[self.SirModel.data[isolated, Cols.isolatedBy] == StatusType.bySymptom]
        isoByWatch = isolated[self.SirModel.data[isolated, Cols.isolatedBy] == StatusType.byWatch]

        infected = self.SirModel.everyone[self.SirModel.data[:, Cols.status] == StatusType.infected]

        nonIsolated = len(infected) - len(isoBySymptom) - len(isoByWatch)
        self.SirModel.RunStats[StatType.nonIsolated,
                               self.SirModel.Sample,
                               day] = nonIsolated

        self.SirModel.RunStats[StatType.isoBySymptom,
                      self.SirModel.Sample,
                      day] = len(isoBySymptom)

        self.SirModel.RunStats[StatType.isoByWatch,
                      self.SirModel.Sample,
                      day] = len(isoByWatch)

        if day % 10 != 0:
            return

        day = 200

        #  make sure the latest controls are on the screen
        ctrlValues = [ctrl.text() for ctrl in self.controls]
        ctrlValues = '\n'.join(ctrlValues)
        self.ctrlValues.setText(ctrlValues)

        infected = self.SirModel.RunStats[
                   StatType.infected,
                   0: self.SirModel.Sample + 1,
                   0:day + 1]

        infected = np.cumsum(infected, axis=1)
        infected = np.mean(infected, axis=0)

        isoBySym = self.SirModel.RunStats[
                   StatType.isoBySymptom,
                   0: self.SirModel.Sample + 1,
                   0:day + 1]
        isoBySym = np.cumsum(isoBySym, axis=1)
        isoBySym = np.mean(isoBySym, axis=0)

        isoByWatch = self.SirModel.RunStats[
                   StatType.isoByWatch,
                   0: self.SirModel.Sample + 1,
                   0:day + 1]
        isoByWatch = np.cumsum(isoByWatch, axis=1)
        isoByWatch = np.mean(isoByWatch, axis=0)

        nonIsolated = self.SirModel.RunStats[
                   StatType.nonIsolated,
                   0: self.SirModel.Sample + 1,
                   0:day + 1]
        nonIsolated = np.cumsum(nonIsolated, axis=1)
        nonIsolated = np.mean(nonIsolated, axis=0)

        days = np.arange(0, day + 1)
        self.canvas.axes.cla()
        self.canvas.axes.set_xlabel('day')
        self.canvas.axes.set_ylabel('Cumulative Counts')
        self.canvas.axes.grid(True)

        self.ax2.cla()
        self.ax2.set_ylabel('Cum Non-isolated')
        self.ax2.yaxis.label.set_color('b')
        self.ax2.tick_params(axis='y', colors='b')

        lns = self.canvas.axes.plot(days, infected[:], 'r', label='<- infected')
        lns += self.canvas.axes.plot(days, isoBySym[:], 'y', label='<- iso by symp')
        lns += self.canvas.axes.plot(days, isoByWatch[:], 'm', label='<- iso by watch')
        lns += self.ax2.plot(days, nonIsolated[:], color='b', linewidth='.5', label='non-iso ->')

        lbls = [line.get_label() for line in lns]
        self.canvas.axes.legend(lns, lbls)

        self.canvas.draw()

    def AddControlNames(self):
        ctrlNames = [str(Ctrls(x)) for x in range(Ctrls.LastCtrl)]
        ctrlNames = ':\n'.join(ctrlNames)
        names = ctrlNames.replace('Ctrls.', '')
        self.ctrlNames.setText(names)
