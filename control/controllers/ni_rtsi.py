import psutil
import signal
import os
import threading
import multiprocessing as mp
import time
import numpy as np
import pandas as pd
from instrumental.drivers.daq.ni import NIDAQ, Task
import traceback


class NIcardRTSI:
    """Controller for NIcards

    Args:
        ports (dict): dict of strings specifying ports which are being used in the type {port_type:port_name} where port type is AI/AO/DI
        rate (int): rate at which the data is output
        data_acquisition_period (num): how often the data is acquired form the card
        getting_data (threading.Event): getting data process flag
        data (dict): dictionary port: data
        data_lock (threading.Lock): data thread lock. Use this whenever directly accessing the data attribute
        staged_signal (dict): data staged for output
        output_signal (dict): data that is currently being outputted
        output_ports (list): list of output ports/5  from ports)
        input_ports (list): list of input ports (derived from ports)
    """

    def __init__(self, ports, name='', rate=10000, data_acquisition_period=0.005,
                 input_buffer_size=100000, output_refresh_time=0.1):
        # name of the controller
        self.name = name
        # rate of NI card
        self.rate = rate
        # max rate of the NI card
        self.output_refresh_time = output_refresh_time
        # save the ports
        if 'AI' not in ports:
            ports['AI'] = []
        if 'AO' not in ports:
            ports['AO'] = []
        if 'DI' not in ports:
            ports['DI'] = []
        self.ports = ports
        self.all_ports = [p for port_category in ports.values()
                          for p in port_category]

        # data acquisition period
        self.data_acquisition_period = data_acquisition_period
        # buffer size
        self.input_buffer_size = input_buffer_size

        # staged data is the data that is going to be written to the outputs when the run starts or is updated.
        self.staged_signal = {out: np.zeros(self.output_refresh_samples) for out in
                              self.ports['AO']}
        # set of events for resetting the index of NI output
        self.index_reset = {out: mp.Event()
                            for out in self.ports['AO']}

        self.output_signal = None
        # reader and writer for the output syncing (gives exact time when the output received the new signal)
        self.output_sync_reader, self.output_sync_sender = mp.Pipe(
            duplex=False)

        # reader and writer for the data being output
        self.output_reader, self.output_writer = mp.Pipe(duplex=False)

        # initiate a list of feedback controllers.
        # feedback senders send the read signal to the receivers (Note: these can be between multiple instances of the
        # NI card, so they have to be separate)
        # receivers have all the information on how to deal with the received signal.
        # needs to be a dictionary of tuples where the first entry is the list of ports and the second pipe writer
        # through which to send it
        self.feedback_senders = dict()
        # needs to be a dictionary of lists where the first entry is a member of the feedback class and the second element
        # is the receiver end of the pipe
        self.feedback_receivers = dict()
        # update feedback pipe is the interface through which each the feedbacks can be changed
        # self.update_feedback_reader, self.update_feedback_writer = mp.Pipe(
        #     duplex=False)
        self.update_feedback_reader, self.update_feedback_writer = None, None

        # create IO process and shutdown event
        self.IO_shutdown = mp.Event()
        # create IO process
        self.IO_process = mp.Process()
        self.IO_process.daemon = False

        # list of ni queues for reading the NI data
        self.queue_list = []

    @property
    def output_refresh_samples(self):
        """Number of samples that are written on every refresh"""
        return int(self.output_refresh_time * self.rate)

    def start(self):
        """Starts the IO process using the staged signal as the output."""
        assert not self.IO_process.is_alive(), 'IO process already running!'

        self.IO_shutdown.clear()

        # create and start IO process
        self.IO_process = mp.Process(target=run_ni_IO, args=(
            self.staged_signal, self.ports, self.output_reader, self.index_reset, self.IO_shutdown, self.queue_list, self.output_sync_sender,
            self.feedback_senders, self.feedback_receivers, self.update_feedback_reader,
            self.rate, self.data_acquisition_period, self.input_buffer_size, self.output_refresh_time))
        self.IO_process.daemon = False
        self.IO_process.start()

        # update the output signal
        self.output_signal = self.staged_signal

    def add_queue(self, p):
        # check that it all makes sense, otherwise will crash the whole thing
        if p.type == 'AO':
            assert all(pn in self.ports[p.type] for pn in p.ports.keys())
        else:
            assert all(pn in self.ports[p.type] for pn in p.ports.keys())

        self.queue_list.append(p)

    # def add_feedback_sender(self, name, ports):
    #     """Creates a pipe, adds writer to the list of feedback senders and returns the reader"""
    #     # reader, writer = mp.Pipe(duplex=False)
    #     reader = None
    #     # self.feedback_senders.update({name: (ports, writer)})
    #     return reader

    # def add_feedback_receiver(self, name, feedback_class, reader):
    #     """
    #     Adds the feedback class to the dictionary of feedback receivers under the given name
    #     """
    #     self.feedback_receivers[name] = [feedback_class, reader]

    # def update_feedback(self, name, feedback_class):
    #     """Updates the dictionary of feedbacks and creates a new pipe if necessary.
    #     Note: if the NI card is running, the new feedbacks won't be started until the card is restarted,
    #     but the existing feedbacks can be updated.
    #     Args:
    #         feedback_class (dict): dictionary of feedback
    #     """
    #     # the feedback already has to exist
    #     assert name in self.feedback_receivers
    #     # update the receivers
    #     self.feedback_receivers[name][0] = feedback_class
    #     # in case the IO process is running, update the feedback class
    #     if self.IO_process.is_alive():
    #         self.update_feedback_writer.send({name: feedback_class})

    def stage_data(self, to_stage, index_reset=True):
        """Takes the dictionary of port:signal where signal is a numpy array in volts and stages it."""
        if isinstance(to_stage, dict):
            for port in to_stage:
                if port in self.ports['AO']:
                    self.staged_signal[port] = to_stage[port]
                else:
                    raise ValueError(
                        'The port {} not one of the defined output channels'.format(port))
                # set the reset events
                if index_reset:
                    self.index_reset[port].set()
        else:
            raise ValueError('to_stage needs to be a dictionary')

    def change_output(self):
        """Updates the output of the currently running signal"""
        assert self.IO_process.is_alive(), "The task needs to be running"
        output = self.staged_signal
        # # update the feedbacks
        # self.update_feedback_writer.send(
        #     {key: fr[0] for key, fr in self.feedback_receivers.items()})
        self.output_writer.send(output)
        start_time = self.output_sync_reader.recv()
        self.output_signal = self.staged_signal
        return start_time

    def stop(self):
        """Stops and zeros all outputs"""
        if self.IO_process.is_alive():
            self.IO_shutdown.set()
            self.IO_process.join()

    def is_running(self):
        """Returns true if IO process running"""
        return self.IO_process.is_alive()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        if self.IO_process.is_alive():
            self.stop()


class NIqueue():
    def __init__(self, ports, port_type):
        """ports are a list of ports queue addresses, type is the type of ports (AO, AI, DI)"""
        self.queue = mp.Queue()
        self.ports = ports
        self.type = port_type
        self.send_labels = ['t'] + list(self.ports.keys())


class QueueListSender:
    def __init__(self, queue_list):
        self.queue_list = queue_list
        self.queue_list_lock = threading.Lock()

    def send(self, result):
        # send the acquired data to the data queue
        self.queue_list_lock.acquire(True)
        for q in self.queue_list:
            if set(q.ports.keys()).issubset(set(result.columns)):
                data = result[q.send_labels].values
                q.queue.put(data)
        self.queue_list_lock.release()


def is_output(port):
    """Checks whether the given port string is output (True) or input (False). Otherwise raises an exception."""
    if port.split('/')[1][:2] == 'ao':
        return True
    elif port.split('/')[1][:2] == 'ai':
        return False
    raise ValueError('The given string is not a port')


def ni_read(task, data_acquisition_period, shutdown, data_sender, feedback_senders):
    """
    Need to document this
    Args:
        feedback_senders: a list of tuples where the first entry is the list of ports and the second
        the writer pipe through which to send the feedback data
    """
    rate = int(np.array(task.fsamp.magnitude))
    last_time = -1 / rate
    try:
        while not shutdown.is_set():
            # read the inputs
            result = task.read(timeout='1s')
            # turn the result to np array
            result = pd.DataFrame.from_dict(
                {key: value for key, value in result.items()})
            # if nothing was picked up, just continue
            if result.shape[0] == 0:
                continue
            result["t"] += last_time + 1 / rate

            last_time = result['t'].iloc[-1]
            # send the results
            data_sender.send(result)
            # # send the feedback
            # for fs in feedback_senders.values():
            #     feedback_data = result.loc[:, fs[0]].iloc[-1, :]
            #     fs[1].send((last_time, feedback_data))

            # wait for the next bit of data
            time.sleep(data_acquisition_period)
    except BrokenPipeError:
        pass
    except:
        traceback.print_exc()
    finally:
        try:
            task.stop()
        except:
            traceback.print_exc()


def format_out(out, t, n_samps, rate):
    # remove units
    out = {key: np.array(v) for key, v in out.items()}
    # add time
    out["t"] = np.linspace(t, t + (n_samps - 1) / rate, n_samps)
    # get to dataframe
    to_send = pd.DataFrame.from_dict(out)
    return to_send

# #TODO: make this work
# def out_feedback(feedback_controllers, feedback_readers, update_feedback_reader, feedback_time, ):
#     # this is to prepare the loop
#     # organise feedback data
#     # dictionary of feedback classes containing methods to calculate corrections
#     feedback_controllers = {
#         key: feedback_receivers[key][0] for key in feedback_receivers}
#     # dictionary of reader pipes to read the feedback
#     feedback_readers = {
#         key: feedback_receivers[key][1] for key in feedback_receivers}
#     # dictionary of corrections containing all the input
#     feedback_corrections = dict()
#     for fc in feedback_controllers.values():
#         feedback_corrections.update({port: 0 for port in fc.output_ports})

#     # this is in the loop
#     # check if the feedback has changed
#     if update_feedback_reader.poll():
#         feedback_controllers.update(update_feedback_reader.recv())
#     # get the error for each port
#     for key, fc in feedback_controllers.items():
#         if feedback_readers[key].poll():
#             # receive the latest signal and flush the pipe of the other ones.
#             # This is just in case that the feedbacks are coming in at a higher rate than they are read.
#             # In that case only the latest feedback signal is taken into account.
#             while feedback_readers[key].poll():
#                 # receive the feedback signal
#                 feedback_time, feedback_signal = feedback_readers[key].recv(
#                 )
#             # get the setpoint at the required time. Start index is index at the time t
#             feedback_index = np.round(
#                 (feedback_time - to_send['t'].iloc[0]) * rate).astype(int)
#             # print(feedback_index)
#             feedback_setpoint = {port: np.take(fc.setpoint[port], start_index[port] + feedback_index, mode='wrap')
#                                     for port in fc.output_ports}
#             # calculate the corrections
#             feedback_corrections.update(fc.calculate_correction(
#                 feedback_setpoint, feedback_signal
#             ))
#             # print('time out: ', t)

#     # adjust the output signal based on pid errors
#     for port, corr in feedback_corrections.items():
#         # get the indices of the ouput
#         output_index = np.take(np.arange(output[port].size), range(
#             start_index[port], start_index[port] + n_samps), mode='wrap')
#         output[port][output_index] += corr
#     out = {port: np.take(value, range(start_index[port], start_index[port] + n_samps), mode='wrap') for
#             port, value in output.items()}
#     # make sure nothing went over 10 with corrections
#     for port in feedback_corrections:
#         out[port][out[port] > 10] = 10
#         out[port][out[port] < -10] = -10


def ni_write(output, task, reader, index_reset, output_refresh_samples, shutdown,
             data_sender, sync_sender, feedback_receivers, update_feedback_reader):
    """Need to doc this!
    For now, output_sync_sender gives the exact time of the start of the outputs. This is important to have good timing!

    Feedback receivers is a list of tuples, the first element of which is the feedback_controller class, and the second element is the pipe receiver from the reader task.
    I am not sure if this is done in the best or clearest way, so really need to document this
    """
    start_index = {port: 0 for port in output.keys()}
    n_samps = 2 * output_refresh_samples
    out = {port: np.take(value, range(start_index[port], start_index[port] + n_samps), mode='wrap') for port, value in
           output.items()}
    start_index = {port: value + n_samps for port,
                   value in start_index.items()}
    try:
        rate = int(np.array(task.fsamp.magnitude))
        # start the first output
        task.write(out, autostart=False)
        task.start()
        t = 0
        # send the acquired data to the data writer
        to_send = format_out(out, t, n_samps, rate)
        t = to_send['t'].iloc[-1]
        data_sender.send(to_send)
        # now start updating the last half of the samples in the buffer
        n_samps = output_refresh_samples
        while not shutdown.is_set():
            # check if there is a new output to receive
            if reader.poll():
                output = reader.recv()
                sync_sender.send(t + 1 / rate)
                # reset the appropriate ports
                for port in output:
                    if index_reset[port].is_set():
                        start_index[port] = 0
                        index_reset[port].clear()
                    # # reset the feedback
                    # if port in feedback_corrections:
                    #     feedback_corrections[port] = 0

            out = {port: np.take(value, range(start_index[port], start_index[port] + n_samps), mode='wrap') for
                   port, value in output.items()}
            start_index = {port: (value + n_samps) % output[port].size for port,
                           value in start_index.items()}
            task.write(out, autostart=False)
            # send the acquired data to the data writer
            to_send = format_out(out, t + 1 / rate, n_samps, rate)
            t = to_send['t'].iloc[-1]

            data_sender.send(to_send)
    except BrokenPipeError:
        pass
    except:
        traceback.print_exc()
    finally:
        try:
            task.stop()
        except:
            traceback.print_exc()


def run_ni_IO(output, ports, output_reader, index_reset_event, shutdown_event, queue_list, output_sync_sender, feedback_senders, feedback_receivers, update_feedback_reader,
              rate=10000, data_acquisition_period=0.005, input_buffer_size=100000, output_refresh_period=0.1, clock_tick_rate=None):
    # set this process to have a high priority
    process = psutil.Process(os.getpid())
    process.nice(psutil.HIGH_PRIORITY_CLASS)
    # how many samples need to be added every refresh time
    output_refresh_samples = int(output_refresh_period * rate)
    # define a queue_list sender
    data_sender = QueueListSender(queue_list)

    # get the set of devices
    devices = {p.split('/')[0] for p in ports['AI'] +
               ports['AO'] + ports['DI']}
    daq = {dev: NIDAQ(dev) for dev in devices}
    # get the set of used ai and ao channels
    channels = [getattr(daq[p.split('/')[0]], p.split('/')[1]) for p in
                ports['AO'] + ports['AI']]
    # add the digital channels
    for p in ports['DI']:
        splitp = p.split('/')
        channels.append(getattr(daq[splitp[0]], splitp[1])[
            int(splitp[2][4:])].as_input())

    # define the task with input and output channels
    task = Task(*channels)
    # set task timing, the recommended NI number of samples is a tenth of a rate
    task.set_timing(fsamp='{}Hz'.format(rate),
                    n_samples=round(rate / 10), mode='continuous')

    # set the output onboard buffer size if there are output channels
    for dev_mtasks in task._mtasks.values():
        if 'AO' in dev_mtasks:
            assert dev_mtasks[
                'AO'].output_onboard_buf_size >= output_refresh_samples, 'Output refresh time * rate should be bigger than the output onboard buffer size: {0}'.format(
                task._mtasks['AO'].output_onboard_buf_size)
            dev_mtasks['AO'].output_onboard_buf_size = int(
                output_refresh_samples)
            # set no regeneration (10158 is no regeneration, 10097 is with)
            dev_mtasks['AO']._mx_task.SetWriteRegenMode(10158)

    # set task buffer size if there are input channels
    try:
        task._mtasks['AI'].input_buf_size = input_buffer_size
    except KeyError:
        pass

    # set up triggers... for some reason this makes the time lag worse. (exactly one step).
    # Maybe should change the trigger edge, but seems to work well without it.
    # task._setup_triggers()

    # prepare the reading and output thread
    input_shutdown = threading.Event()
    output_shutdown = threading.Event()
    input_thread = threading.Thread(target=ni_read, args=(
        task, data_acquisition_period, input_shutdown, data_sender,
        feedback_senders))
    input_thread.daemon = True
    output_thread = threading.Thread(target=ni_write, args=(
        output, task, output_reader, index_reset_event, output_refresh_samples, output_shutdown, data_sender,
        output_sync_sender, feedback_receivers, update_feedback_reader))
    output_thread.daemon = True

    run_output = len(ports['AO']) != 0
    run_input = len(ports['DI'] + ports['AI']) != 0
    try:
        # if there are any outputs, start the output thread. It also starts the task
        if run_output:
            output_thread.start()
        else:
            task.start()

        # need a slight delay so that the input tasks definitely starts after the output task
        time.sleep(0.05)

        # start the acquisiton thread
        if run_input:
            input_thread.start()

        # block until ready to quit
        while not shutdown_event.is_set():
            time.sleep(0.1)
            # close if either of the threads is dead and should be alive
            if (not output_thread.is_alive() and run_output) or (not input_thread.is_alive() and run_input):
                print('One of the threads died! Stopping NI task')
                shutdown_event.set()

    finally:
        try:
            # close the threads
            if output_thread.is_alive():
                output_shutdown.set()
                output_thread.join()
            if input_thread.is_alive():
                input_shutdown.set()
                input_thread.join()
            task.unreserve()
            del task
            if len(ports['AO']) != 0:
                # create a task with only output channels
                channels = [getattr(daq[p.split('/')[0]], p.split('/')[1])
                            for p in ports['AO']]
                task = Task(*channels)
                # reset outputs to 0
                task.set_timing(mode='finite')
                write_data = {out.split(
                    '/')[1]: np.zeros(output_refresh_samples) for out in ports['AO']}
                # write 0's and stop
                task.write(write_data, autostart=True)
                time.sleep(0.1)
                task.stop()
                task.unreserve()
                del task
        finally:
            os.kill(os.getpid(), signal.SIGTERM)
