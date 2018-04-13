#!/usr/bin/python

windowSize = (760, 1050)
windowName = 'Color Selector'

import sys
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import nett_python as nett
from float_message_pb2 import *
from float_vector_message_pb2 import *
from color_table_message_pb2 import *

import helper

class AreaTable(QtGui.QDialog):
    def __init__(self, parent=None):
      super(AreaTable, self).__init__(parent)

      self.setWindowTitle('Region Browser')
      self.resize(windowSize[0], windowSize[1])
      self.AreaTableIndexMap = []
      self.Table = QtGui.QTableWidget()
      self.Table.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers);
      self.Table.cellClicked.connect(self.choose_color)

      self.color_table = {}
      self.color_slot = nett.slot_out_color_table_message('color_table')

    def choose_color(self):
      region_state = {}
      selectionIndex = self.Table.currentRow()
      selectionIndexColumn = self.Table.currentColumn()

      currentSelection = self.Table.selectedIndexes()[0].row()

      if currentSelection not in self.color_table:
        self.color_table[currentSelection] = list()

      if selectionIndexColumn == 0:
        return

      if selectionIndexColumn == 1: #choose color i
        for idx in self.Table.selectedIndexes():
          color = QtGui.QColorDialog.getColor()
          item = QtGui.QTableWidgetItem()
          item.setBackgroundColor(color)
          self.Table.setItem(idx.row(), selectionIndexColumn, item)
          region_state['color_i'] = (color.red(), color.green(), color.blue())

      if selectionIndexColumn == 4: #choose color e
        for idx in self.Table.selectedIndexes():
          color = QtGui.QColorDialog.getColor()
          item = QtGui.QTableWidgetItem()
          item.setBackgroundColor(color)
          self.Table.setItem(idx.row(), selectionIndexColumn, item)
          region_state['color_e'] = (color.red(), color.green(), color.blue())

      if selectionIndexColumn == 3: #choose thickness i
        for idx in self.Table.selectedIndexes():
          num, ok = QInputDialog.getInt(self, "Thickness","Enter a number")
          if ok:
            item = QtGui.QTableWidgetItem()
            item.setText(str(num))
            self.Table.setItem(idx.row(), selectionIndexColumn, item)
            region_state['thickness_i'] = num
          else:
            return

      if selectionIndexColumn == 6: #choose thickness e
        for idx in self.Table.selectedIndexes():
          num, ok = QInputDialog.getInt(self, "Thickness","Enter a number")
          if ok:
            item = QtGui.QTableWidgetItem()
            item.setText(str(num))
            self.Table.setItem(idx.row(), selectionIndexColumn, item)
            region_state['thickness_e'] = num

      if selectionIndexColumn == 2: #choose style i
        for idx in self.Table.selectedIndexes():
          items = ("SolidLine", "DashLine", "DashDotLine", "DashDotDotLine")
          itemChoice, ok = QInputDialog.getItem(self, "Style I", 
                                      "Styles:", items, 0, False)
          if ok:
            item = QtGui.QTableWidgetItem()
            item.setText(str(itemChoice))
            self.Table.setItem(idx.row(), selectionIndexColumn, item)
            region_state['style_i'] = str(itemChoice)
          else:
            return

      if selectionIndexColumn == 5: #choose style e
        for idx in self.Table.selectedIndexes():
          items = ("SolidLine", "DashLine", "DashDotLine", "DashDotDotLine")
          itemChoice, ok = QInputDialog.getItem(self, "Style E", 
                                          "Styles:", items, 0, False)
          if ok:
            item = QtGui.QTableWidgetItem()
            item.setText(str(itemChoice))
            self.Table.setItem(idx.row(), selectionIndexColumn, item)
            region_state['style_e'] = str(itemChoice)
          else:
            return

      self.color_table[currentSelection].append(region_state)
      
    def encode_color_table(self):
      #print self.color_table
      msg = color_table_message()
      print '---------'      
      
      for key in self.color_table:
        region_msg = region_color_message()
        region_msg.region_number = int(key)
        
        for value in self.color_table[key]:
          for k in value:
            if k == 'color_i':
              region_msg.color_i_r = value[k][0]
              region_msg.color_i_g = value[k][1]
              region_msg.color_i_b = value[k][2]
            if k == 'color_e':
              region_msg.color_e_r = value[k][0]
              region_msg.color_e_g = value[k][1]
              region_msg.color_e_b = value[k][2]
            if k == 'thickness_i':
              region_msg.thickness_i = value[k]
            if k == 'thickness_e':
              region_msg.thickness_e = value[k]
            if k == 'style_i':
              region_msg.style_i = str(value[k])
            if k == 'style_e':
              region_msg.style_e = str(value[k])
        msg.value.extend([region_msg])
              
      print msg

      f = open('color_table.bin', "wb")
      f.write(msg.SerializeToString())
      f.close()
      self.color_slot.send(msg.SerializeToString())

    def load_color_table(self):
      f = open('color_table.bin', "rb")
      msg = color_table_message()
      msg.ParseFromString(f.read())
      f.close()

      for x in range(0, len(msg.value)):
        region_state = {}
        item = QtGui.QTableWidgetItem()
        color = QColor(msg.value[x].color_i_r, msg.value[x].color_i_g, msg.value[x].color_i_b)
        item.setBackgroundColor(color)
        self.Table.setItem(msg.value[x].region_number, 1, item)
        region_state['color_i'] = (msg.value[x].color_i_r, msg.value[x].color_i_g, msg.value[x].color_i_b)       

        item = QtGui.QTableWidgetItem()
        color = QColor(msg.value[x].color_e_r, msg.value[x].color_e_g, msg.value[x].color_e_b)
        item.setBackgroundColor(color)
        self.Table.setItem(msg.value[x].region_number, 4, item)
        region_state['color_e'] = (msg.value[x].color_e_r, msg.value[x].color_e_g, msg.value[x].color_e_b)

        item = QtGui.QTableWidgetItem()
        item.setText(msg.value[x].style_i)
        self.Table.setItem(msg.value[x].region_number, 2, item)
        region_state['style_i'] = msg.value[x].style_i

        item = QtGui.QTableWidgetItem()
        item.setText(msg.value[x].style_e)
        self.Table.setItem(msg.value[x].region_number, 5, item)
        region_state['style_e'] = msg.value[x].style_e

        item = QtGui.QTableWidgetItem()
        item.setText(str(msg.value[x].thickness_i))
        self.Table.setItem(msg.value[x].region_number, 3, item)
        region_state['thickness_i'] = msg.value[x].thickness_i

        item = QtGui.QTableWidgetItem()
        item.setText(str(msg.value[x].thickness_e))
        self.Table.setItem(msg.value[x].region_number, 6, item)
        region_state['thickness_e'] = msg.value[x].thickness_e

        if msg.value[x].region_number not in self.color_table:
          self.color_table[msg.value[x].region_number] = list()

        self.color_table[msg.value[x].region_number].append(region_state)

      self.color_slot.send(msg.SerializeToString())
        
    def updateTable(self, areaList):
      self.Table.setRowCount(len(areaList))
      self.Table.setColumnCount(7)
      self.Table.setHorizontalHeaderLabels( ['Region', 'Color I', 'Style I', 'Thickness I', 'Color E', 'Style E', 'Thickness E'] )

      i = 0
      for k in areaList:
        nameOfArea = str(k)
        self.Table.setItem(i, 0, QtGui.QTableWidgetItem(nameOfArea))
        self.AreaTableIndexMap.append( (i, nameOfArea) )
        i = i + 1

      layout = QtGui.QGridLayout()
      layout.addWidget(self.Table)
      self.setLayout(layout)
      self.load_color_table()

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

    def initActions(self):
      self.exitAction = QtGui.QAction('Quit', self)
      self.exitAction.setShortcut('Ctrl+Q')
      self.exitAction.setStatusTip('Exit application')
      self.connect(self.exitAction, QtCore.SIGNAL('triggered()'), self.close)
      self.addAction(self.exitAction)

      self.saveAction = QtGui.QAction('Save and send', self)
      self.saveAction.setShortcut('Ctrl+S')
      self.saveAction.setStatusTip('save and send')
      self.connect(self.saveAction, QtCore.SIGNAL('triggered()'), self.AreaBrowserTable.encode_color_table)
      self.addAction(self.saveAction)

      self.loadAction = QtGui.QAction('Load', self)
      self.loadAction.setShortcut('Ctrl+L')
      self.loadAction.setStatusTip('load')
      self.connect(self.loadAction, QtCore.SIGNAL('triggered()'), self.AreaBrowserTable.load_color_table)
      self.addAction(self.loadAction)

    def createAreaBrowserWindow(self):
      areaBrowserWidget = QtGui.QDockWidget(self)
      areaBrowserWidget.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures)
      areaBrowserWidget.setWindowTitle(QtGui.QApplication.translate("self", "Regions:", None, QtGui.QApplication.UnicodeUTF8))
      self.AreaBrowserTable = AreaTable()
      areaBrowserWidget.setWidget(self.AreaBrowserTable)

      self.addDockWidget(QtCore.Qt.DockWidgetArea(1), areaBrowserWidget)

    def close(self):
      QtGui.qApp.quit()

nett.initialize('tcp://127.0.0.1:2015')

app = QtGui.QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
ip = helper.obtain_ip_address_compute()

area_list_slot_in = nett.slot_in_float_message()
area_list_slot_in.connect('tcp://'+ip+':8000', 'num_regions')

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
