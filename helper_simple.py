import threading
import nett_python as nett
from float_vector_message_pb2 import *
from float_message_pb2 import *
import socket

class observe_slot(threading.Thread):
    
    def __init__(self, slot, message_type):
      super(observe_slot, self).__init__()
      self.slot = slot
      self.msg = message_type
      self.last_message = None
      self.state = False
      self.last_message = None

    def get_last_message(self):
        return self.last_message

    def set_state(self, state):
        self.state = state

    def run(self):
        while True:
          self.msg.ParseFromString( self.slot.receive() )
          if self.msg.value != None:
            self.last_message = self.msg.value
          self.state = not self.state
          self.last_message = self.msg

class observe_growth_rate_slot(threading.Thread):
    def __init__(self, num_regions):
      super(observe_growth_rate_slot, self).__init__()
      self.slot = nett.slot_in_float_vector_message()
      ip = obtain_ip_address_viz()
      print ip
      print num_regions
      self.slot.connect('tcp://'+ip+':2006', 'growth_rate')
      #create dict for the growth_rate
      region_keys = range(0, num_regions)
      self.growth_rate_dict = { key: 0.0001 for key in region_keys }
      self.last_message = None

    def get_last_message(self):
      return self.last_message

    def run(self):
      msg = float_vector_message()
      while True:
        msg.ParseFromString( self.slot.receive() )
        #sanity check
        if len(msg.value) != 1:
          print 'something fishy here'
        if msg.value != None:
          self.last_message = msg.value

        for x in range(0, len(msg.value)):
          self.growth_rate_dict[x] = msg.value[x]
        self.last_message = msg

class observe_eta_slot(threading.Thread):
    def __init__(self, num_regions):
      super(observe_eta_slot, self).__init__()
      self.slot = nett.slot_in_float_vector_message()
      ip = obtain_ip_address_viz()
      self.slot.connect('tcp://'+ip+':2007', 'eta')
      #create dict for the growth_rate
      region_keys = range(0, num_regions)
      self.eta_dict = { key: -30.0 for key in region_keys }
      self.last_message = None

    def get_last_message(self):
      return self.last_message

    def run(self):
      msg = float_vector_message()
      while True:
        msg.ParseFromString( self.slot.receive() )
        #sanity check
        if len(msg.value) != 68:
          print 'something fishy here'
        if msg.value != None:
          self.last_message = msg.value

        for x in range(0, len(msg.value)):
          self.eta_dict[x] = msg.value[x]
        self.last_message = msg

def obtain_ip_address_compute():
	f = open('ip_address_compute.bin','r')
	ip_address_compute = f.read()
        f.close()
	return str(ip_address_compute)

def write_ip_address_viz():
         current_ip = socket.gethostbyname(socket.gethostname())
         f = open('ip_address_viz'+'.bin', "wb")
         f.write(str(current_ip))
         f.close()


def obtain_ip_address_viz():
         f = open('ip_address_viz.bin','r')
         ip_address_compute = f.read()
         f.close()
         return str(ip_address_compute)
