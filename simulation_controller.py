import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore
import nett_python as nett
from float_message_pb2 import *
import subprocess

nett.initialize('tcp://127.0.0.1:2003')

#hard-coded, might be changed later
update_interval_min = 0.1 * 100
update_interval_max = 10000

class SimulationController(QtGui.QWidget):
    
    def __init__(self):
        super(SimulationController, self).__init__()    
        self.init_ui()
        self.init_actions()
        self.quit_slot_out = nett.slot_out_float_message('quit')
        self.pause_slot_out = nett.slot_out_float_message('pause')
        self.reset_slot_out = nett.slot_out_float_message('reset')
        self.update_interval_slot_out = nett.slot_out_float_message('update_interval')
        self.save_slot_out = nett.slot_out_float_message('save')
        #send valid update_interval
        msg = float_message()
        msg.value = update_interval_min
        self.update_interval_slot_out.send(msg.SerializeToString())

                
    def init_ui(self):
        layout = QVBoxLayout()

        self.l1 = QLabel("Update Interval")
        self.l1.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.l1)

        self.sl = QSlider(Qt.Horizontal)
        self.sl.setMinimum(update_interval_min)
        self.sl.setMaximum(update_interval_max)
        self.sl.setValue(1000)
        self.sl.setTickPosition(QSlider.TicksBelow)
        self.sl.setTickInterval(1)
      
        layout.addWidget(self.sl)
        self.sl.valueChanged.connect(self.on_slidervalue_change)
        self.setLayout(layout)
        
        self.pause_button = QtGui.QPushButton('Pause', self)
        self.pause_button.clicked.connect(self.send_pause)
        layout.addWidget(self.pause_button)

        self.quit_button = QtGui.QPushButton('Quit', self)
        self.quit_button.clicked.connect(self.send_quit)
        layout.addWidget(self.quit_button)

        self.reset_button = QtGui.QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.send_reset)
        layout.addWidget(self.reset_button)

        self.start_frplot_button = QtGui.QPushButton('Firing rate Plot', self)
        self.start_frplot_button.clicked.connect(self.start_caplot)
        layout.addWidget(self.start_frplot_button)

        self.start_connectionplot_button = QtGui.QPushButton('Connection Plot', self)
        self.start_connectionplot_button.clicked.connect(self.start_connectionplot)
        layout.addWidget(self.start_connectionplot_button)

        self.start_region_button = QtGui.QPushButton('Region Selector', self)
        self.start_region_button.clicked.connect(self.start_region)
        layout.addWidget(self.start_region_button)

        self.start_eta_button = QtGui.QPushButton('ETA change', self)
        self.start_eta_button.clicked.connect(self.start_eta)
        layout.addWidget(self.start_eta_button)

        self.start_growth_button = QtGui.QPushButton('Growth change', self)
        self.start_growth_button.clicked.connect(self.start_growth)
        layout.addWidget(self.start_growth_button)

        self.save_button = QtGui.QPushButton('Save status', self)
        self.save_button.clicked.connect(self.send_save)
        layout.addWidget(self.save_button)
       
        self.setGeometry(300, 300, 350, 150)
        self.setWindowTitle('SimControl')
        self.show()

    def init_actions(self):
        self.exit_action = QtGui.QAction('Quit', self)
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.setStatusTip('Exit application')
        self.connect(self.exit_action, QtCore.SIGNAL('triggered()'), self.close)
        self.addAction(self.exit_action)

    def on_slidervalue_change(self):
        msg = float_message()
        msg.value = self.sl.value()
        self.update_interval_slot_out.send(msg.SerializeToString())
        print msg

    def send_reset(self):
        msg = float_message()
        msg.value = 1.       
        self.reset_slot_out.send(msg.SerializeToString())
        print 'reset sent'

    def send_quit(self):
        msg = float_message()
        msg.value = 1.       
        self.quit_slot_out.send(msg.SerializeToString())
        print 'quit sent'

    def send_pause(self):
        msg = float_message()
        msg.value = 1.       
        self.pause_slot_out.send(msg.SerializeToString())
        print 'pause sent'

        if str(self.pause_button.text()) == 'Continue':
            self.pause_button.setText('Pause')
        else:
            self.pause_button.setText('Continue')

    def send_save(self):
        msg = float_message()
        msg.value = 1.       
        self.save_slot_out.send(msg.SerializeToString())
        print 'save sent'

    def start_caplot(self):
        subprocess.Popen( ['python', 'fr_plotter.py'], shell=False )

    def start_connectionplot(self):
        subprocess.Popen( ['python', 'connection_plotter.py'], shell=False )

    def start_region(self):
        subprocess.Popen( ['python', 'region_selector.py'], shell=False )
        
    def start_eta(self):
        subprocess.Popen( ['python', 'eta_manipulator.py'], shell=False )

    def start_growth(self):
        subprocess.Popen( ['python', 'growth_rate_manipulator.py'], shell=False )
        
def main():
    
    app = QtGui.QApplication(sys.argv)
    simulation_controller = SimulationController()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
