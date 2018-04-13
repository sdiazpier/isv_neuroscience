import sys
import nett_python as nett
from float_vector_message_pb2 import *
from float_message_pb2 import *
from color_table_message_pb2 import *

import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import helper

use_ip_endpoint = None
fixed_selection = None

if len(sys.argv) != 3:
  print 'switching to default view mode'
  use_ip_endpoint = 'tcp://127.0.0.1:2001'
else:
  print 'using fixed view mode'
  use_ip_endpoint = sys.argv[1]
  fixed_selection = int(sys.argv[2])
 
nett.initialize(use_ip_endpoint)

class MainWindow(QtGui.QMainWindow):
  def __init__(self, parent = None):
    super(MainWindow, self).__init__(parent)

    self.setDockOptions(QtGui.QMainWindow.AnimatedDocks)
    self.setWindowTitle('Firing rate Chart')

    if fixed_selection != None:
      self.setWindowTitle('Firing rate: ' +str(fixed_selection))

    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
  
    win = pg.PlotWidget()
    self.setCentralWidget(win)  

    self.plot = win.getPlotItem()
    self.plot_legend = self.plot.addLegend()

    self.fr_e_data = {}
    self.fr_i_data = {}
    self.curves_e = {}
    self.curves_i = {}
    
    f = open('color_table.bin', "rb")
    msg = color_table_message()
    msg.ParseFromString(f.read())
    f.close()
    self.color_table = msg


    #hack
    for i in range(0,68):
      self.fr_e_data[i] = np.array( [] )
      self.fr_i_data[i] = np.array( [] )

    self.setup_color()
    self.init_actions()
    self.init_menus()

    self.monitor_feed_ = monitor_feed()
    self.connect(self.monitor_feed_, self.monitor_feed_.signal_fr_e, self.update_data_e)
    self.connect(self.monitor_feed_, self.monitor_feed_.signal_fr_i, self.update_data_i)
    self.monitor_feed_.start()

    self.monitor_reset = monitor_reset()
    self.connect(self.monitor_reset, self.monitor_reset.signal, self.reset_data)
    self.monitor_reset.start()

    self.monitor_selection = monitor_selection()
    self.connect(self.monitor_selection, self.monitor_selection.signal, self.set_selection)

    self.monitor_color = monitor_color()
    self.connect(self.monitor_color, self.monitor_color.signal, self.color_update)
    self.monitor_color.start()

    #only listen to update when in non fixed mode
    if fixed_selection == None:
      self.monitor_selection.start()
    else:     
      self.set_selection(float_vector_message()) #fake selection message

  def color_update(self, msg):
    print 'color update!'
    self.color_table = msg
  

  def setup_color(self):
    self.plot.showGrid(x=True, y=True, alpha=0.3)
      
  def init_actions(self):
    self.exit_action = QtGui.QAction('Quit', self)
    self.exit_action.setShortcut('Ctrl+Q')
    self.exit_action.setStatusTip('Exit application')
    self.connect(self.exit_action, QtCore.SIGNAL('triggered()'), self.close)

  def init_menus(self):
    self.addAction(self.exit_action)

  def update_data_i(self, data):
    for x in range(0, len(data.value)):
      self.fr_i_data[x] = np.append(self.fr_i_data[x], data.value[x])

    #only update values in current selection:
    for keys in self.curves_i:
      pen = self.create_pen(keys, False)
         
      self.plot.removeItem(self.curves_i[keys])
      self.curves_i[keys] = self.plot.plot(self.fr_i_data[keys], pen = pen, name = 'i' + str(int(keys)) + ': ' +"{0:.3f}".format(self.fr_i_data[keys][-1]))
      
  def update_data_e(self, data):
    self.plot_legend.scene().removeItem(self.plot_legend)
    self.plot_legend = self.plot.addLegend()
    
    for x in range(0, len(data.value)):
      self.fr_e_data[x] = np.append(self.fr_e_data[x], data.value[x])

    #only update values in current selection:
    for keys in self.curves_e:
      pen = self.create_pen(keys, True)   
      self.plot.removeItem(self.curves_e[keys])
      self.curves_e[keys] = self.plot.plot(self.fr_e_data[keys], pen = pen, name = 'e' + str(int(keys)) + ': ' + "{0:.3f}".format(self.fr_e_data[keys][-1]))

  def create_pen(self, key, is_e):
    pen =  pg.mkPen(color=(0,0,0))
    if self.color_table != None:
        for x in range(0, len(self.color_table.value)):
          if self.color_table.value[x].region_number == key:
            if is_e == True:
              pen = pg.mkPen(color = (self.color_table.value[x].color_e_r, self.color_table.value[x].color_e_g, self.color_table.value[x].color_e_b))
              pen.setWidth(int(self.color_table.value[x].thickness_e))

              if self.color_table.value[x].style_e == "SolidLine":
                pen.setStyle(QtCore.Qt.SolidLine)
              elif self.color_table.value[x].style_e == "DashLine":
                pen.setStyle(QtCore.Qt.DashLine)
              elif self.color_table.value[x].style_e == "DashDotLine":
                pen.setStyle(QtCore.Qt.DashDotLine)
              elif self.color_table.value[x].style_e == "DashDotDotLine":
                pen.setStyle(QtCore.Qt.DashDotDotLine)

            else:
              pen = pg.mkPen(color = (self.color_table.value[x].color_i_r, self.color_table.value[x].color_i_g, self.color_table.value[x].color_i_b))
              pen.setWidth(int(self.color_table.value[x].thickness_i))

              if self.color_table.value[x].style_i == "SolidLine":
                pen.setStyle(QtCore.Qt.SolidLine)
              elif self.color_table.value[x].style_i == "DashLine":
                pen.setStyle(QtCore.Qt.DashLine)
              elif self.color_table.value[x].style_i == "DashDotLine":
                pen.setStyle(QtCore.Qt.DashDotLine)
              elif self.color_table.value[x].style_i == "DashDotDotLine":
                pen.setStyle(QtCore.Qt.DashDotDotLine)
             
            return pen
    
  def reset_data(self):
    self.clear_selection()

  def clear_selection(self):
    self.plot_legend.scene().removeItem(self.plot_legend)
    for keys in self.curves_i:
      self.plot.removeItem(self.curves_i[keys])
    self.curves_i = {}

    for keys in self.curves_e:
      self.plot.removeItem(self.curves_e[keys])
    self.curves_e = {}

    self.plot_legend = self.plot.addLegend()
  
  def set_selection(self, msg):
    if fixed_selection != None:
      msg.value.append(fixed_selection)
    
    self.clear_selection()
          
    for value in msg.value:
      pen = self.create_pen(value, False)
      self.curves_i[value] = self.plot.plot(self.fr_i_data[value], pen = pen, name='i' + str(int(value)) + ': ' +"{0:.3f}".format(self.fr_i_data[value][-1]))

      pen = self.create_pen(value, True)
      self.curves_e[value] = self.plot.plot(self.fr_e_data[value], pen = pen, name = 'e' + str(int(value)) + ': ' +"{0:.3f}".format(self.fr_e_data[value][-1]))
      
class monitor_feed(QtCore.QThread):
  def __init__(self):
    QtCore.QThread.__init__(self)
    self.signal_fr_e = QtCore.SIGNAL("signal_e")
    self.signal_fr_i = QtCore.SIGNAL("signal_i")

    self.fr_e_slot_in = nett.slot_in_float_vector_message()
    self.fr_i_slot_in = nett.slot_in_float_vector_message()
    ip = helper.obtain_ip_address_compute()
    self.fr_e_slot_in.connect('tcp://'+ip+':8000', 'fr_e')
    self.fr_i_slot_in.connect('tcp://'+ip+':8000', 'fr_i')
   
  def run(self):
    msg = float_vector_message()

    while True:
        msg.ParseFromString(self.fr_e_slot_in.receive())
        self.emit(self.signal_fr_e, msg )
        msg = float_vector_message()
        msg.ParseFromString(self.fr_i_slot_in.receive())
        self.emit(self.signal_fr_i, msg )

class monitor_reset(QtCore.QThread):
  def __init__(self):
    QtCore.QThread.__init__(self)
    self.signal = QtCore.SIGNAL("signal")

    self.reset_slot_in = nett.slot_in_float_message()
    self.reset_slot_in.connect('tcp://127.0.0.1:2003', 'reset')
   
  def run(self):
    msg = float_message()
    while True:
        msg.ParseFromString(self.reset_slot_in.receive())
        self.emit(self.signal)
        
class monitor_selection(QtCore.QThread):
  def __init__(self):
    QtCore.QThread.__init__(self)
    self.signal = QtCore.SIGNAL("signal")
    self.area_list_slot_in = nett.slot_in_float_vector_message()
    self.area_list_slot_in.connect('tcp://127.0.0.1:2014', 'regions_selected')
    
  def run(self):
    msg = float_vector_message()
    while True:
      msg.ParseFromString(self.area_list_slot_in.receive())
      self.emit(self.signal, msg)

class monitor_color(QtCore.QThread):
  def __init__(self):
    QtCore.QThread.__init__(self)
    self.signal = QtCore.SIGNAL("signal")

    self.color_slot_in = nett.slot_in_color_table_message()
    self.color_slot_in.connect('tcp://127.0.0.1:2008', 'color_table')
    
  def run(self):
    msg = color_table_message()
    while True:
      msg.ParseFromString(self.color_slot_in.receive())
      self.emit(self.signal, msg)

app = QtGui.QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()

sys.exit(app.exec_())

