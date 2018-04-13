import nest
import numpy
from itertools import izip
from helper import *
from mpi4py import MPI
import ast
import datetime
  
class VirtualConnectome:
    def __init__(self):
        '''
        Simulation parameters
        '''
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        assert(nest.Rank() == self.rank)
        
        # simulation step (ms).
        self.dt = 0.1
        self.number_excitatory_neurons = 32
        self.number_inhibitory_neurons = 8
        self.regions = 68

        # Structural_plasticity properties
        self.update_interval = 1000
        self.record_interval = 1000.0
        # rate of background Poisson input
        self.bg_rate = 11900.0 #From Deco's paper 2014
        self.neuron_model = 'iaf_psc_exp'
	self.G = 0.5

	# Connectivity data
	self.connectivity_filename = 'connectivity_sample.txt'
	self.regions_filename = 'regions_sample.txt'
        '''
        All neurons should have the same homoeostatic rules.
        We want the excitatory populations to fire around 3.06Hz
        From literature, the desired firing rate of the inhibitory populations should be between 8Hz and 15Hz...
        '''
        # Inhibitory synaptic elements of excitatory neurons 
        self.growth_curve_e_i = {
            'growth_curve': "gaussian",
            'growth_rate': -0.01,  # (elements/ms)
            'continuous': False,
            'eta': -3.0,  # Hz
            'eps': 3.0,  # Hz
        }

        # Inhibitory synaptic elements of inhibitory neurons 
        self.growth_curve_i_i = {
            'growth_curve': "gaussian",
            'growth_rate': -0.01,  # (elements/ms)
            'continuous': False,
            'eta': -8.0,  # Hz
            'eps': -7.0,  # Hz
        }

        '''
        Now we specify the neuron model from Deco 2014
        '''
        self.model_params_ex = {'tau_m': 20.0,  # membrane time constant (ms)
                             'tau_syn_ex': 2,  # excitatory synaptic time constant (ms)
                             'tau_syn_in': 10,  # inhibitory synaptic time constant (ms)
                             't_ref': 2.0,  # absolute refractory period (ms)
                             'E_L': -70.0,  # resting membrane potential (mV)
                             'V_th': -50.0,  # spike threshold (mV)
                             'C_m': 500.0,  # membrane capacitance (pF)
                             'V_reset': -55.0,  # reset potential (mV)
                             }

	self.model_params_in = {'tau_m': 25.0,  # membrane time constant (ms)
                             'tau_syn_ex': 2,  # excitatory synaptic time constant (ms)
                             'tau_syn_in': 10,  # inhibitory synaptic time constant (ms)
                             't_ref': 1.0,  # absolute refractory period (ms)
                             'E_L': -70.0,  # resting membrane potential (mV)
                             'V_th': -50.0,  # spike threshold (mV)
                             'C_m': 200.0,  # membrane capacitance (pF)
                             'V_reset': -55.0,  # reset potential (mV)
                             }

        self.nodes_e =  [None] * self.regions
        self.nodes_i  = [None] * self.regions
	self.loc_e = [[] for i in range(self.regions)]
        self.loc_i = [[] for i in range(self.regions)]
	# Create a list to store mean values
        if nest.Rank() == 0:
            self.mean_fr_e = [[] for i in range(self.regions)] 
            self.mean_fr_i = [[] for i in range(self.regions)]
            self.total_connections_e =  [None] * self.regions#[[] for i in range(self.regions)]
            self.total_connections_i =  [None] * self.regions#[[] for i in range(self.regions)]
            self.last_connections_msg = None

        '''
        We initialize variables for the post-synaptic currents of the excitatory, inhibitory and
        external synapses. These values were calculated from a PSP amplitude of 1 for excitatory
        synapses, -1 for inhibitory synapses and 0.11 for external synapses.
        '''
        self.psc_e = 585.0
        self.psc_i = -585.0
        self.psc_ext = 0.62

        self.setup_nett()

    def setup_nett(self):
        '''
	Only needs to happen on rank 0 in MPI setup
	'''
        if nest.Rank() == 0:
            try: #nett already initialized?
                nett.initialize('tcp://127.0.0.1:8000') #2000
            except RuntimeError:
                pass

            self.fr_e_slot_out = nett.slot_out_float_vector_message('fr_e')
            self.fr_i_slot_out = nett.slot_out_float_vector_message('fr_i')
            self.total_connections_slot_out = nett.slot_out_float_vector_message('total_connections')
            self.num_regions_slot_out = nett.slot_out_float_message('num_regions')

            self.run_slot_in = nett.slot_in_float_message()
            self.quit_slot_in = nett.slot_in_float_message()
            self.pause_slot_in = nett.slot_in_float_message()
            self.update_interval_slot_in = nett.slot_in_float_message()
            self.save_slot_in = nett.slot_in_float_message()

            self.quit_slot_in.connect('tcp://127.0.0.1:2003', 'quit')
            self.pause_slot_in.connect('tcp://127.0.0.1:2003', 'pause')
            self.update_interval_slot_in.connect('tcp://127.0.0.1:2003', 'update_interval')
            self.save_slot_in.connect('tcp://127.0.0.1:2003', 'save')

            self.observe_quit_slot = observe_slot(self.quit_slot_in, float_message())
            self.observe_quit_slot.start()
            self.observe_pause_slot = observe_slot(self.pause_slot_in, float_message())
            self.observe_pause_slot.start()
            self.observe_update_interval_slot = observe_slot(self.update_interval_slot_in, float_message())
            self.observe_update_interval_slot.start()
            self.observe_save_slot = observe_slot(self.save_slot_in, float_message())
            self.observe_save_slot.start()

            self.observe_growth_rate_slot = observe_growth_rate_slot(self.regions)
            self.observe_growth_rate_slot.start()
            
            self.observe_eta_slot = observe_eta_slot(self.regions)
            self.observe_eta_slot.start()


    def prepare_simulation(self):
        nest.ResetKernel()
        nest.set_verbosity('M_ERROR')
        nest.SetKernelStatus(
            {
                'resolution': self.dt
            }
        )

        '''
        Set Structural Plasticity synaptic update interval 
	'''
        nest.SetStructuralPlasticityStatus({
            'structural_plasticity_update_interval': self.update_interval,
        })
        '''
        Set Number of virtual processes. Remember SP does not work well with openMP right now, so calls must always be done using mpiexec
	'''
        nest.SetKernelStatus({'total_num_virtual_procs': 8})
        #nest.SetKernelStatus({'total_num_virtual_procs': 1})
        '''
        Now we define Structural Plasticity synapses. One for the inner inhibition of each region and one 
	static synaptic model for the DTI obtained connectivity data. 
        '''
	spsyn_names=['synapse_in'+str(nam) for nam in range(self.regions)]
        nest.CopyModel('static_synapse', 'synapse_ex')
        nest.SetDefaults('synapse_ex', {'weight': self.psc_e*10, 'delay': 1.0})
        sps = {}
	for x in range(0,self.regions) :
		nest.CopyModel('static_synapse', 'synapse_in'+str(x))
        	nest.SetDefaults('synapse_in'+str(x), {'weight': self.psc_i*1000, 'delay': 1.0})
		sps[spsyn_names[x]]= {
		            'model': 'synapse_in'+str(x),
		            'post_synaptic_element': 'Den_in'+str(x),
		            'pre_synaptic_element': 'Axon_in'+str(x),
		        }

	nest.SetStructuralPlasticityStatus({'structural_plasticity_synapses': sps})

    def create_nodes(self):
        '''
        We define the synaptic elements. We have no excitatory synaptic elements, only inhibitory.
	Then we create n populations of ex and inh neurons which represent n regions of the brain.
        '''
	synaptic_elements_e = {}
	synaptic_elements_i = {}
	for x in range(0,self.regions) :
		synaptic_elements_e = {
		    'Den_in'+str(x): self.growth_curve_e_i,
		}
		synaptic_elements_i = {
		    'Axon_in'+str(x): self.growth_curve_i_i,
		}
		self.nodes_e[x] = nest.Create('iaf_psc_alpha', self.number_excitatory_neurons, {
		    'synaptic_elements': synaptic_elements_e	
		})

		self.nodes_i[x] = nest.Create('iaf_psc_alpha', self.number_inhibitory_neurons, {
		    'synaptic_elements': synaptic_elements_i
		})
                self.loc_e[x] = [stat['global_id'] for stat in nest.GetStatus(self.nodes_e[x]) if stat['local']]
                self.loc_i[x] = [stat['global_id'] for stat in nest.GetStatus(self.nodes_i[x]) if stat['local']]
        

    def connect_external_input(self):
        '''
        We create and connect the Poisson generator for external input. It is not very clear which values should be used here... Need to read more on this
        '''
        noise = nest.Create('poisson_generator')
        nest.SetStatus(noise, {"rate": self.bg_rate})
	for x in range(0,self.regions) :
		nest.Connect(noise, self.nodes_e[x], 'all_to_all', {'weight': self.psc_ext*8.42, 'delay': 1.0})
		nest.Connect(noise, self.nodes_i[x], 'all_to_all', {'weight': self.psc_ext*8.7, 'delay': 1.0}) #*1.7
                nest.Connect(self.nodes_e[x], self.nodes_e[x], 'all_to_all', {'weight': self.psc_ext, 'delay': 1.0})


    def connect_inter_region(self):
        '''
        We load the connectivity data from the experimental file and apply this values to the network connections among regions
        '''
	print "loading: "+ self.connectivity_filename
	linecounter = 0
	numbercounter = 0
	target = 0
	num_sources = 0
	source = 0
	cap = 0.0
	with open(self.connectivity_filename, 'r+') as input_file:
	    with open(self.regions_filename, 'r+') as input_file_reg:
		for line, line_reg in izip(input_file, input_file_reg):
		    line = line.strip()
		    line_reg = line_reg.strip()
		    if linecounter !=0:
			    if linecounter % 2 == 1: #Read target region id and number of incoming sources
				numbercounter = 0
				for number in line.split():
					if numbercounter == 0:
						target = int(number)
					else:
						num_sources = int(number)
					numbercounter = numbercounter +1
			    else: #Read cap values
				for number, srs in izip(line.split(),line_reg.split()) :
					source = int(srs)
					cap = float(number)*self.G
					nest.Connect(self.nodes_e[source], self.nodes_e[target], 'all_to_all', {'weight': cap*100, 'delay': 1.0}) #10000 # cap*100
					
		    linecounter = linecounter +1

    def get_num_regions(self):
        return self.regions
    
    def record_fr(self):
        if nest.Rank() == 0:
            msg_fr_e = float_vector_message()
            msg_fr_i = float_vector_message()
	for x in range(0,self.regions) :
            fr_e = nest.GetStatus(self.loc_e[x], 'fr'),  # Firing rate
            fr_e = self.comm.gather(fr_e, root=0)
	    fr_i = nest.GetStatus(self.loc_i[x], 'fr'),  # Firing rate
            fr_i = self.comm.gather(fr_i, root=0)
            if nest.Rank() == 0:
		mean = numpy.mean(list(fr_e))
                #print mean
	        self.mean_fr_e[x].append(mean)
                msg_fr_e.value.append(mean)
                mean = numpy.mean(list(fr_i))
                self.mean_fr_i[x].append(mean)
                msg_fr_i.value.append(mean)
	if nest.Rank() == 0:
            self.fr_e_slot_out.send(msg_fr_e.SerializeToString())
            self.fr_i_slot_out.send(msg_fr_i.SerializeToString())

    def record_connectivity(self):
        if nest.Rank() == 0:
            msg = float_vector_message()
            print nest.GetConnections(self.nodes_i[0], self.nodes_e[0])
	for x in range(0,self.regions) :
	    syn_elems_e = nest.GetStatus(self.loc_e[x], 'synaptic_elements')
	    syn_elems_i = nest.GetStatus(self.loc_i[x], 'synaptic_elements')
            sum_neurons = sum(neuron['Axon_in'+str(x)]['z_connected'] for neuron in syn_elems_i)
            sum_neurons = self.comm.gather(sum_neurons, root=0)
            if nest.Rank() == 0:
	        self.total_connections_i[x] = (sum(sum_neurons))
                msg.value.append(sum(sum_neurons))
        if nest.Rank() == 0:
            self.last_connections_msg = msg
            self.total_connections_slot_out.send(msg.SerializeToString())

    def simulate(self):
        self.update_update_interval()
   
        nest.SetStructuralPlasticityStatus({'structural_plasticity_update_interval': self.update_interval, })

        self.update_growth_rate()
	self.update_eta()

        if nest.Rank()==0:
            print ("Start")
        nest.Simulate(self.record_interval)
        if nest.Rank()==0:
            print ("End")

        self.record_fr()
        self.record_connectivity()

    def update_update_interval(self):
        if nest.Rank() == 0:
            self.update_interval= int(self.observe_update_interval_slot.msg.value)
        else:
            self.update_interval=0
        self.update_interval = self.comm.bcast(self.update_interval, root=0)
        #sanity check
        if self.update_interval == 0:
            self.update_interval = 1000

    def update_growth_rate(self):
        if nest.Rank() == 0:
            growth_rate_dict = self.observe_growth_rate_slot.growth_rate_dict
        else:
            growth_rate_dict = 0
        growth_rate_dict = self.comm.bcast(growth_rate_dict, root=0)
        print growth_rate_dict
        for x in range(0, self.regions) :
            synaptic_elements_e = { 'growth_rate': growth_rate_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Den_in'+str(x):synaptic_elements_e})
	    nest.SetStatus(self.nodes_i[x], 'synaptic_elements_param', {'Axon_in'+str(x):synaptic_elements_e})
	
    def update_eta(self):
        if nest.Rank() == 0:
            eta_dict = self.observe_eta_slot.eta_dict
        else:
            eta_dict = 0
        eta_dict = self.comm.bcast(eta_dict, root=0)
        for x in range(0, self.regions) :
            synaptic_elements_e = { 'eta': eta_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Den_in'+str(x):synaptic_elements_e})
            nest.SetStatus(self.nodes_i[x], 'synaptic_elements_param', {'Axon_in'+str(x):synaptic_elements_e})

    def send_num_regions(self):
        #send out number of regions in each iteration
        msg = float_message()
        msg.value = self.get_num_regions()
        self.num_regions_slot_out.send(msg.SerializeToString())
        
    def get_quit_state(self):
	if nest.Rank() == 0:
            quit_state = self.observe_quit_slot.state
        else:
            quit_state = False
        quit_state = self.comm.bcast(quit_state, root=0)
        return quit_state

    def get_save_state(self):
        save_state = False
	if nest.Rank() != 0:
	    return
        if self.observe_save_slot.state == True:
            self.observe_save_slot.set_state(False)#make it true upon next receive msg in this slot
            save_state = True
        return save_state

    def get_pause_state(self):
        if nest.Rank() == 0:
            pause_state = self.observe_pause_slot.state
        else:
            pause_state = False
        pause_state = self.comm.bcast(pause_state, root=0)
        return pause_state

    def store_connectivity(self, timestamp):
        f = open('connectivity_' + str(timestamp) +'.bin', "wb")
        for x in range(0,self.regions) :
            connections = nest.GetStatus(nest.GetConnections(self.loc_e[x]))
            f.write(str(connections))
        f.close()

    def store_current_connections(self, timestamp):
        f = open('current_connectivity_'+ str(timestamp) +'.bin', "wb")
        f.write(str(self.total_connections_i))
        f.close()

    def store_sp_status(self, timestamp):
        f = open('sp_status_'+ str(timestamp) +'.bin', "wb")
        status = nest.GetStructuralPlasticityStatus({})
        f.write(str(status))
        f.close()
        
    def save_state(self):
        if nest.Rank() != 0:
            return

        print 'saving state to disk'
        time_stamp = str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) #take time stamp only once for all files to make it unique

        update_interval = self.update_interval
        growth_rate = self.observe_growth_rate_slot.growth_rate_dict
        eta_state = self.observe_eta_slot.eta_dict
        f = open('update_interval_'+ str(time_stamp) +'.bin', "wb")
        f.write(str(update_interval))
        f.close()
        f = open('growth_rate_'+ str(time_stamp) +'.bin', "wb")
        f.write(str(growth_rate))
        f.close()

        f = open('eta_state_'+ str(time_stamp) +'.bin', "wb")
        f.write(str(eta_state))
        f.close()

        self.store_connectivity(time_stamp)
        self.store_current_connections(time_stamp)
        self.store_sp_status(time_stamp)
        print 'saving done' 

    def load_sp_state(self):
	if nest.Rank() != 0:
            return
        f = open('sp_status_.bin', 'r')
        var = f.read()
        print str(var)
        status = ast.literal_eval(var)
        nest.SetStructuralPlasticityStatus(status)
        f.close()
        
def run():
    vc = VirtualConnectome()
    vc.prepare_simulation()
    vc.create_nodes()
    vc.connect_external_input()
    vc.connect_inter_region()
    nest.EnableStructuralPlasticity()  
    if nest.Rank() == 0:
        vc.send_num_regions()
    while vc.get_quit_state() == False:
        while vc.get_pause_state() == False:
            vc.simulate()
            if nest.Rank() == 0:
                print 'iteration done'
            if vc.get_save_state() == True:
                vc.save_state()
        
if __name__ == '__main__':
    run()
    print 'simulation ended'
