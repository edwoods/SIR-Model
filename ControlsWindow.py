from enum import IntEnum

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QAbstractItemView, QMessageBox

from FileIO import SaveAsCsv, loadCsv
from SirModel import Ctrls, GetValue

class ScenarioControlsType:
    def __init__(self):
        self.Controls = []
        self.ControlsName = ''
        self.column = 0
        self.nDays = 0

class SceneStatus(IntEnum):
    none,\
    run,\
    end = range(3)

class ControlsWindow(QtWidgets.QMainWindow):

    def __init__(self, controls, SirModel, *args, **kwargs):
        super(ControlsWindow, self).__init__(*args, **kwargs)
        self.resize(740, 495)

        self.controls = controls  # type: list[QtWidgets.QLineEdit]  # the line edits that contain the control values
        self.SirModel = SirModel

        self.Scenario = None  # type: list[ScenarioControlsType]
        self.sceneStatus = SceneStatus.none
        self.SceneDays = 0
        self.nthCtrls = 0

        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)

        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tabWidget.setSizePolicy(sizePolicy)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setMovable(False)
        self.verticalLayout.addWidget(self.tabWidget)
        self.tabWidget.tabCloseRequested.connect(self.CloseTab)

        self.tab = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab, "Default Controls")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(2)

        self.DefaultTable = QtWidgets.QTableWidget(self.tab)
        self.DefaultTable.setColumnCount(20)
        self.DefaultTable.setRowCount(Ctrls.LastCtrl + 1)
        self.DefaultTable.verticalHeader().setVisible(False)
        self.verticalLayout_2.addWidget(self.DefaultTable)

        # self.DefaultTable.selectionModel().selectionChanged.connect(self.SelectChanged)
        self.DefaultTable.itemChanged.connect(self.ItemHasChanged)
        # self.DefaultTable.setSelectionBehavior(QAbstractItemView.SelectColumns)

        self.AddDefaults()

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)

        self.SaveCtrls = QtWidgets.QPushButton(self)
        self.SaveCtrls.setText("Save Controls")
        self.horizontalLayout.addWidget(self.SaveCtrls)
        self.SaveCtrls.clicked.connect(self.SaveControls)
        self.SaveCtrls.setShortcut('Ctrl+S')

        self.DuplicateCol = QtWidgets.QPushButton(self)
        self.DuplicateCol.setText("Duplicate Selection")
        self.horizontalLayout.addWidget(self.DuplicateCol)
        self.DuplicateCol.clicked.connect(self.DuplicateColumn)
        self.DuplicateCol.setShortcut('Ctrl+D')

        self.ApplyCurrentSelection = QtWidgets.QPushButton(self)
        self.ApplyCurrentSelection.setText("Apply Current Selection")
        self.horizontalLayout.addWidget(self.ApplyCurrentSelection)
        self.ApplyCurrentSelection.clicked.connect(self.ApplySelected)
        self.ApplyCurrentSelection.setShortcut('Alt+L')

        self.OpenFileButton = QtWidgets.QPushButton(self)
        self.OpenFileButton.setText("Open File")
        self.horizontalLayout.addWidget(self.OpenFileButton)
        self.OpenFileButton.clicked.connect(self.OpenFile)
        self.verticalLayout.addLayout(self.horizontalLayout)

    def ItemHasChanged(self):
        self.DefaultTable.resizeColumnsToContents()

    def LoadScenario(self, colFrom):
        # load the names of the controls and their column number is a dictionary
        nCols = self.DefaultTable.columnCount()
        ColVsName = {}
        for col in range(1, nCols):
            item = self.DefaultTable.item(0, col)
            if not item:
                continue

            ColVsName[item.text()] = col

        keys = ColVsName.keys()

        # get the control sets associated with the selected scenario
        nRows = self.DefaultTable.rowCount()
        Scene = []
        for row in range(1, nRows):
            item = self.DefaultTable.item(row, colFrom)
            if not item or item.text() == '':     # end of scenario
                break

            if item.text() not in keys:
                QMessageBox.warning(None, "Controls missing",
                                    "There is no control list named: \n'" +
                                    item.text() + "' in the selected scenario")
                break

            # load the controls for this key
            cCol = ColVsName[item.text()]
            scnCtrls = ScenarioControlsType()
            scnCtrls.ControlsName = item.text()
            scnCtrls.column = cCol
            scnCtrls.nDays = self.DefaultTable.item(row, colFrom + 1).text()
            scnCtrls.Controls = []
            Scene.append(scnCtrls)
            for cRow in range(1, nRows+1):
                cItem = self.DefaultTable.item(cRow, cCol)
                if not cItem or cItem.text() == '':  # should not happen
                    break

                text = cItem.text()
                scnCtrls.Controls.append(cItem.text())

        self.Scenario = Scene
        self.FirstDay()

    def CopySceneControls(self):
        for row in range(int(Ctrls.LastCtrl) ):
            text = self.Scenario[self.nthCtrls].Controls[row]
            self.controls[row].setText(text)

        self.SirModel.SetCntrls()

    def NextDay(self):
        self.SceneDays += 1
        if GetValue(self.Scenario[self.nthCtrls].nDays) < self.SceneDays:
            self.nthCtrls += 1
            if self.nthCtrls >= len(self.Scenario):
                self.sceneStatus = SceneStatus.end
                self.nthCtrls = 0
                return

            self.SceneDays = 0
            self.CopySceneControls()

    def FirstDay(self):
        self.SceneDays = 0
        self.nthCtrls = 0
        self.sceneStatus = SceneStatus.run

        self.CopySceneControls()

    def ApplySelected(self):
        colFrom = self.DefaultTable.currentColumn()
        item = self.DefaultTable.item(0, colFrom)
        if not item or item.text() == '':
            return

        if item.text() == 'Scenario':
            self.LoadScenario(colFrom)
            return

        self.Scenario = None

        # copy the values from the selected column over to the MainWindow
        for row in range(1, int(Ctrls.LastCtrl+ 1)):
            item = self.DefaultTable.item(row, colFrom)
            if not item:
                continue
            self.controls[row - 1].setText(item.text())

        self.SirModel.ResetStats = True
        self.SirModel.SetCntrls()
        # self.SirModel.ctrlsChanged = True

    def SaveControls(self):
        SaveAsCsv('Sir Controls.csv', self.DefaultTable)

    def OpenFile(self):
        data = loadCsv()

        nrows = len(data)
        ncols = len(data[0])

        font = QtGui.QFont()
        font.setWeight(68)

        for row in range(nrows):
            for col in range(ncols):
                text = data[row][col]
                item = QtWidgets.QTableWidgetItem(text)

                if row == 0:
                    item.setFont(font)

                if col == 0:
                    item.setFont(font)
                    item.setFlags(QtCore.Qt.ItemIsEnabled)

                self.DefaultTable.setItem(row, col, item)

    def DuplicateColumn(self):
        colFrom = self.DefaultTable.currentColumn()
        row = self.DefaultTable.currentRow()

        if self.DefaultTable.item(0,colFrom).text() == '':
            return

        nCols = self.DefaultTable.columnCount()
        nRows = self.DefaultTable.rowCount()

        # find and empty column
        cols = [icol for icol in range(colFrom + 1, nCols) if self.DefaultTable.item(0, icol).text() == '']
        if len(cols) == 0:
            return

        colTo = cols[0]
        item = QtWidgets.QTableWidgetItem('Ctrls.' + str(colTo)) # a name for the 2nd set of controls
        self.DefaultTable.setItem(0, colTo, item)

        for irow in range(1,nRows):
            item = self.DefaultTable.item(irow, colFrom)
            if not item:
                continue

            item = QtWidgets.QTableWidgetItem(item.text())
            self.DefaultTable.setItem(irow, colTo, item)

        self.DefaultTable.resizeColumnsToContents()

    def AddDefaults(self):
        self.DefaultTable.horizontalHeader().setVisible(False)
        self.DefaultTable.verticalHeader().setVisible(False)

        header = self.DefaultTable.horizontalHeader()
        header.setStyleSheet("QHeaderView::section { border-bottom: 1px solid gray; }")
        header.sortIndicatorChanged.connect(lambda index, order, x=self.DefaultTable: self.sortChanged(index, order, x))

        from PyQt5.QtWidgets import QFrame
        header.setFrameStyle(QFrame.Box | QFrame.Plain)

        ctrlNames = [str(Ctrls(x)) for x in range(Ctrls.LastCtrl)]
        ctrlVals = Ctrls.GetDefaults()

        rows = self.DefaultTable.rowCount()
        font = QtGui.QFont()
        # font.setBold(True)
        font.setWeight(68)
        brush = QtGui.QBrush(QtGui.QColor(199, 199, 199))
        brush.setStyle(QtCore.Qt.NoBrush)

        item = QtWidgets.QTableWidgetItem('Ctrl Name')
        item.setFont(font)
        item.setFlags(QtCore.Qt.ItemIsEnabled)
        self.DefaultTable.setItem(0, 0, item)

        item = QtWidgets.QTableWidgetItem('Defaults')
        item.setBackground(brush)
        self.DefaultTable.setItem(0, 1, item)

        for n in range(int(Ctrls.LastCtrl)):
            pName = ctrlNames[n].split('.')[1]  # e.g. pName = 'Cntrls.nPeeps' just need 'nPeeps'
            pVal = GetValue(ctrlVals[n])  # pVal of the nth Cntrl

            item = QtWidgets.QTableWidgetItem(pName)
            item.setTextAlignment(QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
            item.setFont(font)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.DefaultTable.setItem(n+1, 0, item)

            item = QtWidgets.QTableWidgetItem(str(pVal))
            # item.setData(QtCore.Qt.EditRole, pVal)
            self.DefaultTable.setItem(n+1, 1, item)

        self.DefaultTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.DefaultTable.resizeColumnsToContents()
        self.DefaultTable.resizeRowsToContents()

        self.DefaultTable.setAlternatingRowColors(True)
        self.DefaultTable.setStyleSheet("alternate-background-color: linen; background-color: white;")

    def closeEvent(self, event):
        self.hide()
        # event.accept()

    def CloseTab(self, index):
        tab = self.tabWidget.widget(index)
        tab.deleteLater()
        self.tabWidget.removeTab(index)

    def sortChanged(self, index, order, table):
        pass
