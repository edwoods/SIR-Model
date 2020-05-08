import csv
import os
from os import path
from pathlib import Path

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

def GetFilename(fileName):
    # do not over write the input file
    if not path.exists(fileName):
        return fileName

    baseName = Path(fileName).stem

    # create a new name for the file
    version = 1
    while True:
        newName = baseName + '.v' + str(version) + '.csv'
        version += 1
        if not path.exists(newName):
            return newName


def SaveAsCsv(fileName, table):
    # table = QtWidgets.QTableWidget()
    # do not over write the input file
    outName = GetFilename(fileName)
    if not outName:
        return

    with open(outName, 'w', newline='') as file:
        writer = csv.writer(file)

        # line = [] *table.columnCount()
        # for col in range(table.columnCount()):
        #     line[col] = table.horizontalHeaderItem(col).text()

        for row in range(table.rowCount()):
            line = [''] * table.rowCount()
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    line[col] = table.item(row, col).text()

            writer.writerow(line)

def loadCsv():
    fileExtension = 'csv'
    path = os.path.normpath(os.getcwd())
    fileName, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open " + fileExtension, path,
                                                        fileExtension.upper() + "(*." + fileExtension + ")")

    if not fileName:
        return None

    list1 = []
    with open(fileName, "r") as fileInput:
        for row in csv.reader(fileInput):
            list1.append(row)

    return list1
