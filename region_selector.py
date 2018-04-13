#!/usr/bin/python

windowSize = (150, 1050)
windowName = 'Region Browser'

import sys
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import Qt
import nett_python as nett
from float_message_pb2 import *
from float_vector_message_pb2 import *
import subprocess
import helper

class AreaTable(QtGui.QDialog):
    def __init__(self, parent=None):
      super(AreaTable, self).__init__(parent)

      self.setWindowTitle('Region Browser')
      self.resize(windowSize[0], windowSize[1])
      self.AreaTableIndexMap = []
      self.Table = QtGui.QTableWidget()
      self.Table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers);
      self.Table.cellClicked.connect(self.cellClicked)
      self.Table.cellDoubleClicked.connect(self.start_chart)

    def cellClicked(self):
      selectionIndex = self.Table.currentRow()
      selectionIndexColumn = self.Table.currentColumn()

      if selectionIndexColumn == 0:
        msg = float_vector_message()

        rows=[]
        for idx in self.Table.selectedIndexes():
          rows.append(idx.row())
          msg.value.append(float(self.AreaTableIndexMap[idx.row()][1]))

        area_list_slot_out.send(msg.SerializeToString())

    def start_chart(self):
      selectionIndex = self.Table.currentRow()
      selectionIndexColumn = self.Table.currentColumn()

      if selectionIndexColumn == 0:
        msg = float_vector_message()

        rows=[]
        for idx in self.Table.selectedIndexes():
          region_number = int(self.AreaTableIndexMap[idx.row()][1])
          subprocess.Popen( ['python', 'ca_plotter.py', 'tcp://127.0.0.1:2000' +str(region_number), str(region_number)], shell=False )

    def updateTable(self, areaList):
      self.Table.setRowCount(len(areaList))
      self.Table.setColumnCount(1)
      self.Table.setHorizontalHeaderLabels( ['Region'] )

      i = 0
      for k in areaList:
        nameOfArea = str(k)
        self.Table.setItem(i, 0, QtGui.QTableWidgetItem(nameOfArea))
        self.AreaTableIndexMap.append( (i, nameOfArea) )
        i = i + 1

      layout = QtGui.QGridLayout()
      layout.addWidget(self.Table)
      self.setLayout(layout)

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
      super(MainWindow,self).__init__(parent)

      self.resize(windowSize[0], windowSize[1])
      self.setWindowTitle(windowName)

      self.setDockOptions(QtGui.QMainWindow.AnimatedDocks)
      self.centralwidget = QtGui.QWidget(self)
      self.centralwidget.hide()
      self.setCentralWidget(self.centralwidget)
      self.createAreaBrowserWindow()

      self.initActions()
      self.initMenus()

    def initActions(self):
      self.exitAction = QtGui.QAction('Quit', self)
      self.exitAction.setShortcut('Ctrl+Q')
      self.exitAction.setStatusTip('Exit application')
      self.connect(self.exitAction, QtCore.SIGNAL('triggered()'), self.close)
      self.addAction(self.exitAction)

    def initMenus(self):
        pass
        #menuBar = self.menuBar()
        #fileMenu = menuBar.addMenu('&File')
        #fileMenu.addAction(self.exitAction)

    def createAreaBrowserWindow(self):
      areaBrowserWidget = QtGui.QDockWidget(self)
      areaBrowserWidget.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
      areaBrowserWidget.setWindowTitle(QtGui.QApplication.translate("self", "Regions:", None, QtGui.QApplication.UnicodeUTF8))
      self.AreaBrowserTable = AreaTable()
      areaBrowserWidget.setWidget(self.AreaBrowserTable)

      self.addDockWidget(QtCore.Qt.DockWidgetArea(1), areaBrowserWidget)

    def close(self):
      QtGui.qApp.quit()

app = QtGui.QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
ip = helper.obtain_ip_address_compute()
print str(ip)
nett.initialize('tcp://127.0.0.1:2014')
print str(ip)
area_list_slot_in = nett.slot_in_float_message()
print str(ip)
area_list_slot_in.connect('tcp://'+ip+':8000', 'num_regions')
area_list_slot_out = nett.slot_out_float_vector_message('regions_selected')

print 'waiting for region list...'
msg = float_message()
msg.ParseFromString(area_list_slot_in.receive())
areaList = []
for i in range(0, int(msg.value)):
  areaList.append(str(i))
print 'received!'

mainWindow.AreaBrowserTable.updateTable(areaList)

if __name__ ==  "__main__":
  app.exec_()
  sys.exit()
