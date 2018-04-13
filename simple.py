import nest
import numpy
from itertools import izip
from helper_simple import *
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
	self.regions = 1

        # Structural_plasticity properties
        self.update_interval = 100
        self.record_interval = 1000.0
        # rate of background Poisson input
        self.bg_rate = 10000.0
        self.neuron_model = 'iaf_psc_exp'

        '''
        In this implementation of structural plasticity, neurons grow
        connection points called synaptic elements. Synapses can be created
        between compatible synaptic elements. The growth of these elements is
        guided by homeostatic rules, defined as growth curves.
        Here we specify the growth curves for synaptic elements of excitatory
        and inhibitory neurons.
        '''
        # Excitatory synaptic elements of excitatory neurons
        self.growth_curve_e_e = {
            'growth_curve': "gaussian",
            'growth_rate': 0.0001,  # (elements/ms)
            'continuous': False,
            'eta': 0.0,  # Hz
            'eps': 5.0,  # Hz
        }

        # Inhibitory synaptic elements of excitatory neurons
        self.growth_curve_e_i = {
            'growth_curve': "gaussian",
            'growth_rate': 0.0001,  # (elements/ms)
            'continuous': False,
            'eta': 0.0,  # Ca2+
            'eps': self.growth_curve_e_e['eps'],  # Ca2+
        }

        # Excitatory synaptic elements of inhibitory neurons
        self.growth_curve_i_e = {
            'growth_curve': "gaussian",
            'growth_rate': 0.0004,  # (elements/ms)
            'continuous': False,
            'eta': 0.0,  # Hz
            'eps': 20.0,  # Hz
        }

        # Inhibitory synaptic elements of inhibitory neurons
        self.growth_curve_i_i = {
            'growth_curve': "gaussian",
            'growth_rate': 0.0001,  # (elements/ms)
            'continuous': False,
            'eta': 0.0,  # Hz
            'eps': self.growth_curve_i_e['eps']  # Hz
        }

        '''
        Now we specify the neuron model.
        '''
        self.model_params = {'tau_m': 10.0,  # membrane time constant (ms)
                             # excitatory synaptic time constant (ms)
                             'tau_syn_ex': 0.5,
                             # inhibitory synaptic time constant (ms)
                             'tau_syn_in': 0.5,
                             't_ref': 2.0,  # absolute refractory period (ms)
                             'E_L': -65.0,  # resting membrane potential (mV)
                             'V_th': -50.0,  # spike threshold (mV)
                             'C_m': 250.0,  # membrane capacitance (pF)
                             'V_reset': -65.0  # reset potential (mV)
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
            self.save_state = False

        '''
        We initialize variables for the post-synaptic currents of the
        excitatory, inhibitory and external synapses. These values were
        calculated from a PSP amplitude of 1 for excitatory synapses,
        -1 for inhibitory synapses and 0.11 for external synapses.
        '''
        self.psc_e = 585.0
        self.psc_i = -585.0
        self.psc_ext = 6.2

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

            self.fr_e_slot_out = nett.slot_out_float_vector_message('fr_e')
            self.fr_i_slot_out = nett.slot_out_float_vector_message('fr_i')
            self.total_connections_slot_out = nett.slot_out_float_vector_message('total_connections_i')
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
        
        all_e_nodes = nest.Create('iaf_psc_alpha', self.number_excitatory_neurons*self.regions)
        all_i_nodes = nest.Create('iaf_psc_alpha', self.number_inhibitory_neurons*self.regions)
        
	for x in range(0,self.regions) :
		synaptic_elements_e = {
		    'Den_ex'+str(x): self.growth_curve_e_e,
                    'Den_in'+str(x): self.growth_curve_e_i,
                    'Axon_ex'+str(x): self.growth_curve_e_e,
		}
		synaptic_elements_i = {
                    'Den_ex'+str(x): self.growth_curve_i_e,
                    'Den_in'+str(x): self.growth_curve_i_i,
		    'Axon_in'+str(x): self.growth_curve_i_i,
		}

		self.nodes_e[x] = all_e_nodes[x*self.number_excitatory_neurons:(x+1)*self.number_excitatory_neurons]
                self.nodes_i[x] = all_i_nodes[x*self.number_inhibitory_neurons:(x+1)*self.number_inhibitory_neurons]

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
            msg_fr_e = float_vector_message()
            msg_fr_i = float_vector_message()
	for x in range(0,self.regions) :
            fr_e = nest.GetStatus(self.loc_e[x], 'fr'),  # Firing rate
            fr_e = self.comm.gather(fr_e, root=0)
	    fr_i = nest.GetStatus(self.loc_i[x], 'fr'),  # Firing rate
            fr_i = self.comm.gather(fr_i, root=0)
            if nest.Rank() == 0:
		mean = numpy.mean(list(fr_e))
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

        self.update_growth_rate()
	self.update_eta()

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
        for x in range(0, self.regions) :
            if nest.Rank() == 0:
	        print("GR"+str(growth_rate_dict[x]))
            synaptic_elements_e = { 'growth_rate': growth_rate_dict[x], }
            synaptic_elements_i = { 'growth_rate': -growth_rate_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Den_in'+str(x): synaptic_elements_i})
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Den_ex'+str(x): synaptic_elements_e})
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Axon_ex'+str(x): synaptic_elements_e})
	    nest.SetStatus(self.nodes_i[x], 'synaptic_elements_param', {'Axon_in'+str(x):synaptic_elements_e})
            nest.SetStatus(self.nodes_i[x], 'synaptic_elements_param', {'Den_in'+str(x):synaptic_elements_i})
            nest.SetStatus(self.nodes_i[x], 'synaptic_elements_param', {'Den_ex'+str(x):synaptic_elements_e})

    def update_eta(self):
        if nest.Rank() == 0:
            eta_dict = self.observe_eta_slot.eta_dict
        else:
            eta_dict = 0
        eta_dict = self.comm.bcast(eta_dict, root=0)
        for x in range(0, self.regions) :
            synaptic_elements_e = { 'eta': eta_dict[x], }
            nest.SetStatus(self.nodes_e[x], 'synaptic_elements_param', {'Den_in'+str(x): synaptic_elements_e})
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
    i_counter = 1
    vc = VirtualConnectome()
    vc.prepare_simulation()
    vc.create_nodes()
    vc.connect_external_input()
    nest.EnableStructuralPlasticity()  
    while vc.get_quit_state() == False:
        while vc.get_pause_state() == False:
            vc.simulate()
            if nest.Rank() == 0:
                print('Iteration '+str(i_counter)+' finished\n')
            i_counter=i_counter+1
            if vc.get_save_state() == True:
                vc.store_current_connections()
        
if __name__ == '__main__':
    run()
    print 'simulation ended'
