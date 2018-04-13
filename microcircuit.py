import nest
import numpy
from itertools import izip
from helper import *
from mpi4py import MPI
import ast
  
class VirtualConnectome:
    def __init__(self):

	self.comm = MPI.COMM_WORLD
        self.rank = self.comm.Get_rank()
        assert(nest.Rank() == self.rank)
        '''
        We define general simulation parameters
        '''
        # simulated time (ms)
        self.t_sim = 200000.0
        # simulation step (ms).
        self.dt = 0.1
        self.number_excitatory_neurons = 800
        self.number_inhibitory_neurons = 200
	self.regions = 4

        # Structural_plasticity properties
        self.update_interval = 1000
        self.record_interval = 1000.0
        # rate of background Poisson input
        self.bg_rate = 10000.0
        self.neuron_model = 'iaf_psc_exp'

	######################################
	##         Network parameters      ###
	######################################

	# area of network in mm^2; scales numbers of neurons
	# use 1 for the full-size network (77,169 neurons)
	area = 0.1 #0.02

	layer_names = ['L23', 'L4', 'L5', 'L6']
	population_names = ['e', 'i']

	self.full_scale_num_neurons = [
	    [int(20683*area),  # layer 2/3 e
	     int(5834*area)],  # layer 2/3 i
	    [int(21915*area),  # layer 4 e
	     int(5479*area)],  # layer 4 i
	    [int(4850*area),   # layer 5 e
	     int(1065*area)],  # layer 5 i
	    [int(14395*area),  # layer 6 e
	     int(2948*area)]   # layer 6 i
	]

	# mean EPSP amplitude (mV) for all connections except L4e->L2/3e
	#PSP_e = 0.15
	# mean EPSP amplitude (mv) for L4e->L2/3e connections
	# see p. 801 of the paper, second paragraph under 'Model Parameterization',
	# and the caption to Supplementary Fig. 7
	#PSP_e_23_4 = PSP_e * 2
	# standard deviation of PSC amplitudes relative to mean PSC amplitudes
	#PSC_rel_sd = 0.1
	# IPSP amplitude relative to EPSP amplitude
	#self.g = -4.0

	# whether to use full-scale in-degrees when downscaling the number of neurons
	# When preserve_K is false, the full-scale connection probabilities are used.
	preserve_K = False

	# probabilities for >=1 connection between neurons in the given populations
	# columns correspond to source populations; rows to target populations
	# source      2/3e    2/3i    4e      4i      5e      5i      6e      6i
	conn_probs = [[0.1009, 0.1689, 0.0437, 0.0818, 0.0323, 0.0,    0.0076, 0.0],
		      [0.1346, 0.1371, 0.0316, 0.0515, 0.0755, 0.0,    0.0042, 0.0],
		      [0.0077, 0.0059, 0.0497, 0.135, 0.0067,  0.0003, 0.0453, 0.0],
		      [0.0691, 0.0029, 0.0794, 0.1597, 0.0033, 0.0,    0.1057, 0.0],
		      [0.1004, 0.0622, 0.0505, 0.0057, 0.0831, 0.3726, 0.0204, 0.0],
		      [0.0548, 0.0269, 0.0257, 0.0022, 0.06,   0.3158, 0.0086, 0.0],
		      [0.0156, 0.0066, 0.0211, 0.0166, 0.0572, 0.0197, 0.0396, 0.2252],
		      [0.0364, 0.001,  0.0034, 0.0005, 0.0277, 0.008,  0.0658, 0.1443]]

	# mean dendritic delays for excitatory and inhibitory transmission (ms)
	self.delays = [1.5, 0.75]
	# standard deviation relative to mean delays
	self.delay_rel_sd = 0.5
	# connection pattern used in connection calls connecting populations
	self.conn_dict = {'rule': 'fixed_total_number'}
	# weight distribution of connections between populations
	self.weight_dict_exc = {'distribution': 'normal_clipped', 'low': 0.0}
	self.weight_dict_inh = {'distribution': 'normal_clipped', 'high': 0.0}
	# delay distribution of connections between populations
	self.delay_dict = {'distribution': 'normal_clipped', 'low': 0.1}

	# (eta, eps) parameters for each population
    	self.gaussian_set_points = [[(-0.05, 0.005),   # 2/3e_e
                            (-0.2,  0.02)],   # 2/3e_i
                           [(-0.26, 0.026),   # 4e_e
                            (-0.45, 0.045)],  # 4e_i
                           [(-0.55, 0.05),   # 5e_e
                            (-0.5,  0.055)],   # 5e_i #this might lead to strange connectivity
                           [(-0.35, 0.035),   # 6e_e
                            (-0.59, 0.059)]]  # 6e_i
	
        '''
        In this implementation of structural plasticity, neurons grow
        connection points called synaptic elements. Synapses can be created
        between compatible synaptic elements. The growth of these elements is
        guided by homeostatic rules, defined as growth curves.
        Here we specify the growth curves for synaptic elements of excitatory
        and inhibitory neurons.
        '''
     	# Parameters for the synaptic elements
	self.growth_curve_e_e = {
	'growth_curve': "gaussian",
	'growth_rate': 0.0018, #excitatory synaptic elements of Excitatory neurons
	'continuous': False,
	}

	# Parameters for the synaptic elements
	self.growth_curve_e_i = {
	'growth_curve': "gaussian",
	'growth_rate': 0.001, #inhibitory synaptic elements of Excitatory neurons
	'continuous': False,
	}

	# Parameters for the synaptic elements
	self.growth_curve_i_e = {
	'growth_curve': "gaussian",
	'growth_rate': 0.0025, #excitatory synaptic elements of Inhibitory neurons
	'continuous': False,
	}

	# Parameters for the synaptic elements
	self.growth_curve_i_i = {
	'growth_curve': "gaussian",
	'growth_rate': 0.001, #inhibitory synaptic elements of Inhibitory neurons
	'continuous': False,
	}

        '''
        Now we specify the neuron model.
        '''
	self.model_params = {'tau_m': 10.0,      # membrane time constant (ms)
		        'tau_syn_ex': 0.5,  # excitatory synaptic time constant (ms)
		        'tau_syn_in': 0.5,  # inhibitory synaptic time constant (ms)
		        't_ref': 2.0,       # absolute refractory period (ms)
		        'E_L': -65.0,       # resting membrane potential (mV)
		        'V_th': -50.0,      # spike threshold (mV)
		        'C_m': 250.0,       # membrane capacitance (pF)
		        'V_reset': -65.0,   # reset potential (mV)
	}

        self.nodes_e =  [None] * self.regions
        self.nodes_i  = [None] * self.regions
	self.loc_e = [[] for i in range(self.regions)]
        self.loc_i = [[] for i in range(self.regions)]
	# Create a list to store mean values
        if nest.Rank() == 0:
            self.mean_ca_e = [[] for i in range(self.regions)] 
            self.mean_ca_i = [[] for i in range(self.regions)]
            self.total_connections_e =  [None] * self.regions#[[] for i in range(self.regions)]
            self.total_connections_i =  [None] * self.regions#[[] for i in range(self.regions)]
            self.last_connections_msg = None
            self.save_state = False

        '''
        We initialize variables for the post-synaptic currents of the
        excitatory, inhibitory and external synapses. These values were
        calculated from a PSP amplitude of 1 for excitatory synapses,
        -1 for inhibitory synapses and 0.11 for external synapses.
        '''
        self.psc_e = 585.0
        self.psc_i = -585.0
        #self.psc_ext = 6.2
	self.psc_ext = 15.0#5.85

	self.setup_nett()

    def setup_nett(self):
        '''
	Only needs to happen on rank 0 in MPI setup
	'''
        if nest.Rank() == 0:
            try: #nett already initialized?
                current_ip = socket.gethostbyname(socket.gethostname())
		current_ip = '127.0.0.1'
		print(current_ip)
                f = open('ip_address_compute'+'.bin', "wb")
                f.write(str(current_ip))
                f.close()
                nett.initialize('tcp://'+str(current_ip)+':8000')
		#nett.initialize('tcp://127.0.0.1:8000')
            except RuntimeError:
                pass

            self.ca_e_slot_out = nett.slot_out_float_vector_message('ca_e')
            self.ca_i_slot_out = nett.slot_out_float_vector_message('ca_i')
            self.total_connections_slot_out = nett.slot_out_float_vector_message('total_connections')
	    self.total_connections_e_slot_out = nett.slot_out_float_vector_message('total_connections_e')
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
        '''
        We set global kernel parameters. Here we define the resolution
        for the simulation, which is also the time resolution for the update
        of the synaptic elements.
        '''
        nest.SetKernelStatus(
            {
                'resolution': self.dt
            }
        )
	'''
        Set Number of virtual processes. Remember SP does not work well with openMP right now, so calls must always be done using mpiexec
        '''
        nest.SetKernelStatus({'total_num_virtual_procs': self.comm.Get_size() })
        print( "Total number of virtual processes set to: " +str(self.comm.Get_size()))

        '''
        Set Structural Plasticity synaptic update interval which is how often
        the connectivity will be updated inside the network. It is important
        to notice that synaptic elements and connections change on different
        time scales.
        '''
        nest.SetStructuralPlasticityStatus({
            'structural_plasticity_update_interval': self.update_interval,
	    'tau_Ca': 10000.0,
            'beta_Ca': 0.001,
        })

        '''
        Now we define Structural Plasticity synapses. In this example we create
        two synapse models, one for excitatory and one for inhibitory synapses.
        Then we define that excitatory synapses can only be created between a
        pre synaptic element called 'Axon_ex' and a post synaptic element
        called Den_ex. In a similar manner, synaptic elements for inhibitory
        synapses are defined.
        '''
	spsyn_names=['synapse_in'+str(nam) for nam in range(self.regions)]
	spsyn_names_e=['synapse_ex'+str(nam) for nam in range(self.regions)]
        sps = {}
	for x in range(0,self.regions) :
                nest.CopyModel('static_synapse', 'synapse_in'+str(x))
                nest.SetDefaults('synapse_in'+str(x), {'weight': self.psc_i, 'delay': 1.0})
		nest.CopyModel('static_synapse', 'synapse_ex'+str(x))
        	nest.SetDefaults('synapse_ex'+str(x), {'weight': self.psc_e, 'delay': 1.0})
                sps[spsyn_names[x]]= {
		            'model': 'synapse_in'+str(x),
		            'post_synaptic_element': 'Den_in'+str(x),
		            'pre_synaptic_element': 'Axon_in'+str(x),
                }
                sps[spsyn_names_e[x]]= {
		            'model': 'synapse_ex'+str(x),
		            'post_synaptic_element': 'Den_ex'+str(x),
		            'pre_synaptic_element': 'Axon_ex'+str(x),
                }
	nest.SetStructuralPlasticityStatus({'structural_plasticity_synapses': sps})

    def create_nodes(self):
        '''
        Now we assign the growth curves to the corresponding synaptic elements
        '''
	synaptic_elements_e = {}
        synaptic_elements_i = {}
        
        for x in range(0,self.regions) :
		# Excitatory pop, excitatory elems
		gc_e_e = self.growth_curve_e_e.copy()
		gc_e_e['eta'] = self.gaussian_set_points[x][0][0]
                gc_e_e['eps'] = self.gaussian_set_points[x][0][1]
		# Inhibitory pop, inhibitory elems
		gc_i_i = self.growth_curve_i_i.copy()
		gc_i_i['eta'] = self.gaussian_set_points[x][1][0]
                gc_i_i['eps'] = self.gaussian_set_points[x][1][1]
		# Excitatory pop, inhibitory elems
		gc_e_i = self.growth_curve_e_i.copy()
		gc_e_i['eta'] = self.gaussian_set_points[x][0][0]
                gc_e_i['eps'] = self.gaussian_set_points[x][0][1]
		# Inhibitory pop, excitatory elems
		gc_i_e = self.growth_curve_i_e.copy()
		gc_i_e['eta'] = self.gaussian_set_points[x][1][0]
                gc_i_e['eps'] = self.gaussian_set_points[x][1][1]
		synaptic_elements_e = {
		    'Den_ex'+str(x): gc_e_e,
                    'Den_in'+str(x): gc_e_i,
                    'Axon_ex'+str(x): gc_e_e,
		}
		synaptic_elements_i = {
                    'Den_ex'+str(x): gc_i_e,
                    'Den_in'+str(x): gc_i_i,
		    'Axon_in'+str(x): gc_i_i,
		}

		self.nodes_e[x] = nest.Create(self.neuron_model, self.number_excitatory_neurons, {
		    'synaptic_elements': synaptic_elements_e
		})

		self.nodes_i[x] = nest.Create(self.neuron_model, self.number_inhibitory_neurons, {
		    'synaptic_elements': synaptic_elements_i
		})
                self.loc_e[x] = [stat['global_id'] for stat in nest.GetStatus(self.nodes_e[x]) if stat['local']]
                self.loc_i[x] = [stat['global_id'] for stat in nest.GetStatus(self.nodes_i[x]) if stat['local']]
		nest.SetStatus(self.loc_e[x], {'synaptic_elements': synaptic_elements_e})
                nest.SetStatus(self.loc_i[x], {'synaptic_elements': synaptic_elements_i})

    def connect_external_input(self):
        '''
        We create and connect the Poisson generator for external input
        '''
        noise = nest.Create('poisson_generator')
        nest.SetStatus(noise, {"rate": self.bg_rate})
	for x in range(0,self.regions) :
            nest.Connect(noise, self.nodes_e[x], 'all_to_all',
                     {'weight': self.psc_ext, 'delay': 1.0})
            nest.Connect(noise, self.nodes_i[x], 'all_to_all',
                     {'weight': self.psc_ext, 'delay': 1.0})



    def get_num_regions(self):
        return self.regions
    
    def record_ca(self):
        if nest.Rank() == 0:
            msg_ca_e = float_vector_message()
            msg_ca_i = float_vector_message()
	for x in range(0,self.regions) :
            ca_e = nest.GetStatus(self.loc_e[x], 'Ca'),  # Calcium concentration
            ca_e = self.comm.gather(ca_e, root=0)
	    ca_i = nest.GetStatus(self.loc_i[x], 'Ca'),  # Calcium concentration
            ca_i = self.comm.gather(ca_i, root=0)
            if nest.Rank() == 0:
		print(ca_e)
                mean = numpy.mean(list(ca_e))
                #print mean
	        self.mean_ca_e[x].append(mean)
                msg_ca_e.value.append(mean)
                mean = numpy.mean(list(ca_i))
                self.mean_ca_i[x].append(mean)
                msg_ca_i.value.append(mean)
	if nest.Rank() == 0:
            self.ca_e_slot_out.send(msg_ca_e.SerializeToString())
            self.ca_i_slot_out.send(msg_ca_i.SerializeToString())

    def record_connectivity(self):
        if nest.Rank() == 0:
            msg_i = float_vector_message()
            msg_e = float_vector_message()
	for x in range(0,self.regions) :
	    syn_elems_e = nest.GetStatus(self.loc_e[x], 'synaptic_elements')
	    syn_elems_i = nest.GetStatus(self.loc_i[x], 'synaptic_elements')
            sum_neurons_e = sum(neuron['Axon_ex'+str(x)]['z_connected'] for neuron in syn_elems_e)
            sum_neurons_e = self.comm.gather(sum_neurons_e, root=0)
	    sum_neurons_i = sum(neuron['Axon_in'+str(x)]['z_connected'] for neuron in syn_elems_i)
            sum_neurons_i = self.comm.gather(sum_neurons_i, root=0)
            
            if nest.Rank() == 0:
	        self.total_connections_i[x] = (sum(sum_neurons_i))
                msg_i.value.append(sum(sum_neurons_i))
		self.total_connections_e[x] = (sum(sum_neurons_e))
                msg_e.value.append(sum(sum_neurons_e))
        if nest.Rank() == 0:
            self.total_connections_e_slot_out.send(msg_e.SerializeToString())
            self.last_connections_msg = msg_i
            self.total_connections_slot_out.send(msg_i.SerializeToString())

    def simulate(self):
        if nest.Rank() == 0:
            self.send_num_regions()
        self.update_update_interval()
   
        nest.SetStructuralPlasticityStatus({'structural_plasticity_update_interval': self.update_interval, })

        #self.update_growth_rate()
	#self.update_eta()

        nest.Simulate(self.record_interval)
        
        self.record_ca()
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
	#print str(nest.Rank()) + ": " + str(growth_rate_dict)
        for x in range(0, self.regions) :
	    print("GR"+str(growth_rate_dict[x]))
            synaptic_elements_e = { 'growth_rate': growth_rate_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'update_synaptic_elements', synaptic_elements_e)
	    nest.SetStatus(self.nodes_i[x], 'update_synaptic_elements', synaptic_elements_e)

    def update_eta(self):
        if nest.Rank() == 0:
            eta_dict = self.observe_eta_slot.eta_dict
        else:
            eta_dict = 0
        eta_dict = self.comm.bcast(eta_dict, root=0)
        for x in range(0, self.regions) :
            synaptic_elements_e = { 'eta': eta_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'update_synaptic_elements', synaptic_elements_e)

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
	if nest.Rank() != 0:
	    return
        result = False
        if bool(self.save_state) != bool(self.observe_save_slot.state):
            self.save_state = not self.save_state
            result = True
        return result

    def get_pause_state(self):
        if nest.Rank() == 0:
            pause_state = self.observe_pause_slot.state
        else:
            pause_state = False
        pause_state = self.comm.bcast(pause_state, root=0)
        return pause_state

    def store_connectivity(self):
        if nest.Rank() == 0:
            f = open('connectivity_'+'.bin', "wb")#+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            for x in range(0,self.regions) :
                connections = nest.GetStatus(nest.GetConnections(self.loc_e[x]))
                f.write(str(connections))
            f.close()

    def store_current_connections(self):
        if nest.Rank() == 0:
            f = open('current_connectivity_'+'.bin', "wb")#+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            f.write(str(self.total_connections_i))
            f.close()

    def store_sp_status(self):
        if nest.Rank() == 0:
            f = open('sp_status_'+'.bin', "wb")#+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            status = nest.GetStructuralPlasticityStatus({})
            f.write(str(status))
            f.close()
        
    def save_state(self):
        if nest.Rank() != 0:
            return
        update_interval = self.observe_update_interval_slot.get_last_message()
        growth_rate = self.observe_growth_rate_slot.get_last_message()
        eta_state = self.observe_eta_slot.get_last_message()
        if update_interval != None:
            f = open('update_interval_'+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            f.write(update_interval.SerializeToString())
            f.close()
        if growth_rate != None:
            f = open('growth_rate_'+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            f.write(growth_rate.SerializeToString())
            f.close()

        if eta_state != None:
            f = open('eta_state_'+ str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")) +'.bin', "wb")
            f.write(eta_state.SerializeToString())
            f.close()     

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
    nest.EnableStructuralPlasticity()  
    while vc.get_quit_state() == False:
        while vc.get_pause_state() == False:
            vc.simulate()
            if nest.Rank() == 0:
                print 'iteration done'
            if vc.get_save_state() == True:
                vc.store_current_connections()
        
if __name__ == '__main__':
    run()
    print 'simulation ended'
