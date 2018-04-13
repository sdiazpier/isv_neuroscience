import nett_python as nett
from float_vector_message_pb2 import *
from float_message_pb2 import *
from color_table_message_pb2 import *

import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import helper_simple

nett.initialize('tcp://127.0.0.1:2002')

class MainWindow(QtGui.QMainWindow):
  def __init__(self, parent = None):
    super(MainWindow,self).__init__(parent)

    self.setDockOptions(QtGui.QMainWindow.AnimatedDocks)
    self.setWindowTitle('Connections')

    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')
    
    win = pg.PlotWidget()
    self.setCentralWidget(win)  

    self.plot = win.getPlotItem()

    self.connection_data_i = {}
    self.connection_data_e = {}

    #hack
    for i in range(0,68):
      self.connection_data_i[i] = np.array( [] )
      self.connection_data_e[i] = np.array ( [] )
   
    self.connection_curve_i = {}
    self.connection_curve_e = {}

    self.setup_color()
    self.init_actions()
    self.init_menus()

    self.monitor_feed_ = monitor_feed()
    self.connect(self.monitor_feed_, self.monitor_feed_.signal_conn_i, self.update_data_i)
    self.connect(self.monitor_feed_, self.monitor_feed_.signal_conn_e, self.update_data_e)
    self.monitor_feed_.start()

    self.monitor_reset = monitor_reset()
    self.connect(self.monitor_reset, self.monitor_reset.signal, self.reset_data)
    self.monitor_reset.start()

    self.monitor_selection = monitor_selection()
    self.connect(self.monitor_selection, self.monitor_selection.signal, self.set_selection)
    self.monitor_selection.start()

    self.monitor_color = monitor_color()
    self.connect(self.monitor_color, self.monitor_color.signal, self.color_update)
    self.monitor_color.start()

    self.plot_legend = self.plot.addLegend()
    f = open('color_table.bin', "rb")
    msg = color_table_message()
    msg.ParseFromString(f.read())
    f.close()
    self.color_table = msg

  def color_update(self, msg):
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

  def clear_selection(self):
    for keys in self.connection_curve_e:
      self.plot.removeItem(self.connection_curve_e[keys])
      self.plot_legend.removeItem(self.connection_curve_e[keys].name())
    self.connection_curve_e = {}
    for keys in self.connection_curve_i:
      self.plot.removeItem(self.connection_curve_i[keys])
      self.plot_legend.removeItem(self.connection_curve_i[keys].name())
    self.connection_curve_i = {}  

  def set_selection(self, msg):
    self.clear_selection()
    pen = pg.mkPen(color=(255, 0,0))
    for value in msg.value:
      self.connection_curve_e[value] = self.plot.plot(self.connection_data_e[value], pen = self.create_pen(value, True), name = 'e' +str(int(value)))
      self.connection_curve_i[value] = self.plot.plot(self.connection_data_i[value], pen = self.create_pen(value, False), name = 'i' +str(int(value)))

  def create_pen(self, key, is_e):
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
                  pen = pg.mkPen(color = (self.color_table.value[x].color_i_r, self.color_table.value[x].color_e_g, self.color_table.value[x].color_i_b))
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

  def update_data_i(self, data):
    self.plot_legend.scene().removeItem(self.plot_legend)
    self.plot_legend = self.plot.addLegend()

    for x in range(0, len(data.value)):
      self.connection_data_i[x] = np.append(self.connection_data_i[x], data.value[x])

    #update active curves only:
    for keys in self.connection_curve_i:
      self.plot.removeItem(self.connection_curve_i[keys])
      self.plot_legend.removeItem(self.connection_curve_i[keys].name())
      self.connection_curve_i[keys] = self.plot.plot(self.connection_data_i[keys], pen = self.create_pen(keys, False), name = 'i' +str(int(keys)))

  def update_data_e(self, data):
    for x in range(0, len(data.value)):
      self.connection_data_e[x] = np.append(self.connection_data_e[x], data.value[x])

    #update active curves only:
    for keys in self.connection_curve_e:
      self.plot.removeItem(self.connection_curve_e[keys])
      self.plot_legend.removeItem(self.connection_curve_e[keys].name())
      self.connection_curve_e[keys] = self.plot.plot(self.connection_data_e[keys], pen = self.create_pen(keys, True), name = 'e' +str(int(keys)))

  def reset_data(self):
    self.plot_legend.scene().removeItem(self.plot_legend)
    for keys in self.connection_data_e:
      self.connection_data_e[keys] = np.array( [] )
      self.plot_legend.removeItem(self.connection_curve_e[keys].name())
    for keys in self.connection_data_i:
      self.connection_data_i[keys] = np.array( [] )
      self.plot_legend.removeItem(self.connection_curve_i[keys].name())
    self.plot_legend = self.plot.addLegend()

class monitor_feed(QtCore.QThread):
  def __init__(self):
    QtCore.QThread.__init__(self)
    self.signal_conn_e = QtCore.SIGNAL("signal_e")
    self.signal_conn_i = QtCore.SIGNAL("signal_i")

    self.connection_slot_e_in = nett.slot_in_float_vector_message()
    self.connection_slot_i_in = nett.slot_in_float_vector_message()
    ip = helper_simple.obtain_ip_address_compute()
    self.connection_slot_e_in.connect('tcp://'+ip+':8000', 'total_connections_e')
    self.connection_slot_i_in.connect('tcp://'+ip+':8000', 'total_connections_i')
   
  def run(self):
    while True:
        msg = float_vector_message()
        msg.ParseFromString(self.connection_slot_i_in.receive())
        self.emit(self.signal_conn_i, msg )
        msg = float_vector_message()
        msg.ParseFromString(self.connection_slot_e_in.receive())
        self.emit(self.signal_conn_e, msg )

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

