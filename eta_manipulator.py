import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore

import nett_python as nett
from float_vector_message_pb2 import *
import helper

class Slider(QtGui.QSlider):
  def __init__(self, orientation, number, parent = None):
    super(QtGui.QSlider, self).__init__(orientation, parent)
    self.number = number
    self.valueChanged[int].connect(self.value_change)
    self.signal = QtCore.SIGNAL("signal")

  def value_change(self, value):
    self.emit(self.signal, self.number, value )

class ETAManipulator(QtGui.QWidget):
  
    def __init__(self):
      super(ETAManipulator, self).__init__()
      self.value_label = {}
      self.num_regions = 68
      self.init_ui()
      self.eta_dict = {}
      region_keys = range(0, self.num_regions)
      self.eta_dict = { key: -40.0 for key in region_keys }
      self.slot_out = nett.slot_out_float_vector_message('eta')
              
    def init_ui(self):
      main_layout = QVBoxLayout()

      for x in range(0, self.num_regions):
        if x % 16 == 0:
          layout = QHBoxLayout()

        self.create_slider(layout, x)
        main_layout.addLayout(layout)

      self.setLayout(main_layout)
      self.setWindowTitle('ETA')
      self.show()

    def create_slider(self, layout, number):
      layout_inner = QVBoxLayout()

      label = QtGui.QLabel(self)
      label.setText(str(number))
      layout_inner.addWidget(label) 
      
      sld = Slider(QtCore.Qt.Vertical, number, self)
      sld.setMinimum(0)
      sld.setMaximum(40)
      sld.setValue(40)
      self.connect(sld, sld.signal, self.change_value)
      layout_inner.addWidget(sld)
           
      valueLabel = QtGui.QLabel(self)
      valueLabel.setText(str(-40 / 1.))
      layout_inner.addWidget(valueLabel)
      self.value_label[number] = valueLabel
      layout.addLayout(layout_inner)
      
        
    def change_value(self, slider_number, value):
      self.eta_dict[slider_number] = -( value / 1. )
      self.send_rates()
      self.value_label[slider_number].setText(str(self.eta_dict[slider_number]))
      

    def send_rates(self):
      print self.eta_dict
      msg = float_vector_message()
      for key in self.eta_dict:
        msg.value.append(self.eta_dict[key])
      self.slot_out.send(msg.SerializeToString())

def main():
  
    app = QtGui.QApplication(sys.argv)
    ex = ETAManipulator()
    sys.exit(app.exec_())


if __name__ == '__main__':
  helper.write_ip_address_viz()
  ip = helper.obtain_ip_address_viz()
  nett.initialize('tcp://' + str(ip) + ':2007')
  main()    

