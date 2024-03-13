from numpy.lib.function_base import select
from control.controllers import *
import numpy as np
from ..instrument import Instrument
from control.exceptions import *
from datetime import datetime
import time
import warnings
import traceback
import threading
import pandas as pd


class NIinst(Instrument):
    """Class defining instruments connected to the NI card

        The class inherits Instrument class

        Args:
            ports (str, list of str): list of ports the device takes on the NI card
            type (str): type of an instrument. It can be one of: "analog_input", "analog_output" or "digital_input". Digital outputs not yet supported.
            calibration (function): a handle to a function taking an voltages and outputting physically meaningful values
    """

    def __init__(self, controller, port_type, ports, flushing_time=10, read=True, subsample=1, feedback=None, **kwargs):
        """Assigns the controller, ports and any of the attributes inherited by the Instrument class

            Args:
                controller (NIcard): NIcards class instance defined in the controllers module
                port_type (str, list_like):  list of ports the device takes on the NI card. Needs to be a predefined port
                                            in the NIcards object. It is recommended that dictionaries are used for
                                            easier later readability, but this is not a requirement.
                subsample (int): a number of samples to average over before saving to memory. Smoothens out the data and reduces memory footprint. 1 is no subsampling.
                **kwargs: keyword arguments specified by the Instrument class
        """
        assert isinstance(controller, NIcard) or isinstance(
            controller, NIcardRTSI), "Wrong controller passed"
        Instrument.__init__(self, controller=controller, **kwargs)
        # add the rate to its property
        self.rate = controller.rate
        # add the port type
        self.port_type = port_type
        if isinstance(ports, list):
            # if haven't given the names to the ports, just use default names
            ports = {p: p for p in ports}
        assert isinstance(
            ports, dict), "Ports should be a dictionary or a list!"

        # check if all passed ports are valid
        for p in ports:
            assert p in controller.ports[port_type], "Port %r is not a port defined in the controller" % p

        # # if it is output, rename so that it corresponds to the way the ports are written/read
        # if self.port_type == "AO":
        #     # for some reason, AO have different port naming. Should change that in the future
        #     self.ports = {
        #         key.split('/')[1]: value for key, value in ports.items()}
        # else:
        #     self.ports = ports
        self.ports = ports

        # prepare data queue
        # subsample variable if we want to only preserve the means of every sample (useful for temperature and slow
        #  moving variables
        self.ni_queue = NIqueue(
            self.ports, self.port_type)
        # prepare the subsampling variable to reduce the data kept
        self.subsample = int(subsample)
        # readjust your rate based on the number of subsamples
        self.rate = self.rate / subsample

        # prepare the list of times of the data stream
        self.data_times = np.empty([0, 2])
        # prepare the data reading thread, locks and events
        self.data_lock = threading.Lock()
        self.update_data_thread = threading.Thread(
            target=self.update_data_worker)
        self.update_data_thread.daemon = True
        self.stop_data_thread = threading.Event()
        # set the flushing time (which defines data_stream and how many samples per second)
        self.set_flushing_time(flushing_time)

        # prepare the feedback if it exists
        assert feedback is None
        self.feedback = feedback
        # if feedback is not None:
        #     assert self.port_type in {
        #         "AO", "DO"}, "Only output instruments can have feedback!"
        # prepare the outputting thread for when a transient signal is outputted (this is when the calibration is returning a list)
        self.outputting_thread = threading.Thread()
        self.outputting_thread.daemon = True
        self.outputting_thread_stop = threading.Event()

        if read:
            self.controller.add_queue(self.ni_queue)
            self.update_data_thread.start()

    # flushing time is a property that changes how much data is kept in memory. Note: changing the flushing time flushes all data in memory!
    @property
    def flushing_time(self):
        return self._flushing_time

    @flushing_time.setter
    def flushing_time(self, value):
        self.set_flushing_time(value)

    def set_flushing_time(self, value):
        self.data_lock.acquire(True)
        # if we are setting for the first time, just define the attributes.
        # Otherwise, keep the current data stream and copy to a new length
        if not hasattr(self, 'data_stream'):
            # create new data stream
            self.samples_in_memory = int(
                np.round(value * self.rate))
            self.data_stream = np.zeros(
                (self.samples_in_memory, len(self.ports) + 1)).astype(float)
            self.final_data_indx = -1
        else:
            old_samples_in_memory = self.samples_in_memory
            # get the old data stream
            start_data_indx = (self.final_data_indx +
                               1) % old_samples_in_memory
            if start_data_indx <= self.final_data_indx:
                old_data_stream = self.data_stream[start_data_indx:self.final_data_indx + 1, :]
            else:
                old_data_stream = np.vstack((self.data_stream[start_data_indx:, :],
                                             self.data_stream[:self.final_data_indx + 1, :]))

            # create the new data stream and keep the old data
            self.samples_in_memory = int(
                np.round(value * self.rate))
            # create the new data stream, but keep the old data
            self.data_stream = np.zeros(
                (self.samples_in_memory, len(self.ports) + 1)).astype(float)
            if old_samples_in_memory >= self.samples_in_memory:
                self.data_stream = old_data_stream[-self.samples_in_memory:]
                self.final_data_indx = self.samples_in_memory - 1
            else:
                self.data_stream[:old_samples_in_memory] = old_data_stream
                self.final_data_indx = old_samples_in_memory - 1
        self.data_lock.release()
        self._flushing_time = value

    def update_data_worker(self):
        try:
            result_leftover = np.empty((0, len(self.ports) + 1))
            while not self.stop_data_thread.is_set():
                # get the data from the queue (should be in numpy format)
                result = self.ni_queue.queue.get(block=True)

                self.data_lock.acquire(True)
                # subsample if needed
                if self.subsample != 1:
                    result = np.vstack((result_leftover, result))
                    n_take = len(result) - (len(result) % self.subsample)
                    result_leftover = result[n_take:, :]
                    if n_take == 0:
                        continue
                    result = result[:n_take, :]
                    # take a mean of bucketed elements in buckets subsample size
                    result = np.apply_along_axis(lambda m: np.mean(
                        m.reshape(-1, self.subsample), axis=1), axis=0, arr=result)
                n_samples = result.shape[0]

                start_new_data_indx = (
                    self.final_data_indx + 1) % self.samples_in_memory
                final_new_data_indx = (
                    start_new_data_indx + n_samples) % self.samples_in_memory

                # append the new data
                if final_new_data_indx > start_new_data_indx:
                    self.data_stream[start_new_data_indx:final_new_data_indx, :] = result
                elif final_new_data_indx < start_new_data_indx:
                    delta_indx = self.samples_in_memory - start_new_data_indx
                    self.data_stream[start_new_data_indx:,
                                     :] = result[:delta_indx]
                    self.data_stream[:final_new_data_indx,
                                     :] = result[delta_indx:]
                else:
                    self.data_stream = result
                self.final_data_indx = (
                    final_new_data_indx - 1) % self.samples_in_memory
                self.data_lock.release()
        except:
            traceback.print_exc()
            warnings.warn('An error occurred while reading the instrument: ' +
                          self.name + " Stopping reading thread")

    def get_raw_data(self, start_time=0, end_time=-1):
        """Returns the hard-copied NI data in a pandas DF

            Args:
                start_time: the starting time of data points
                end_time: the last time taken. -1 means the last time acquired
            Returns:
                0-th row is always time, n-th row corresponds to the n-th port in self.ports
        """
        self.data_lock.acquire(True)
        last_data_time = self.data_stream[self.final_data_indx, 0]
        start_data_indx = (self.final_data_indx
                           + 1) % self.samples_in_memory
        start_data_time = self.data_stream[start_data_indx, 0]
        # if still starting up, change the start index to 0
        if start_data_time <= 0:
            start_data_indx = 0
            start_data_time = self.data_stream[start_data_indx, 0]
        if last_data_time == 0 or start_time > last_data_time or (end_time > 0 and end_time <= start_data_time):
            # have not started acquiring data yet, the start time is bigger than the latest time,
            # or end time smaller than the first time in memory; return empty
            self.data_lock.release()
            return pd.DataFrame(columns=self.ports.values())
        # find the end index
        if end_time < 0 or end_time > last_data_time:
            # return up until the latest time in the memory
            indx_end = self.final_data_indx
        else:
            delta_indx = np.round((last_data_time - end_time) *
                                  self.rate).astype(int)
            indx_end = (self.final_data_indx -
                        delta_indx) % self.samples_in_memory
        # if start time negative, assume it's the current time - wanted start time
        if start_time < 0:
            start_time = last_data_time + start_time
        # find the start index
        if start_time <= start_data_time:
            indx_start = start_data_indx
        else:
            delta_indx = np.round(
                (last_data_time - start_time) * self.rate).astype(int)
            indx_start = (self.final_data_indx
                          - delta_indx) % self.samples_in_memory
            # sometimes it can happen that the rate is not perfectly uniform because of the

        # get the data and format it in the pandas dataframe
        if indx_start < indx_end:
            selected_data = self.data_stream[indx_start:indx_end, :]
        elif indx_start > indx_end:
            selected_data = np.vstack(
                (self.data_stream[indx_start:, :], self.data_stream[:indx_end, :]))
        else:
            selected_data = self.data_stream[indx_start, :][np.newaxis, :]

        data_out = pd.DataFrame(
            selected_data[:, 1:], columns=self.ports.values(), index=pd.Index(data=selected_data[:, 0], name='t'), copy=True)
        self.data_lock.release()
        return data_out

    def get_last_data_point(self):
        self.data_lock.acquire(True)
        last_data_time = self.data_stream[self.final_data_indx, 0]
        # have not started acquiring data yet, return empty
        if last_data_time == 0:
            self.data_lock.release()
            return pd.DataFrame(columns=self.ports.values())
        data_out = self.data_stream[self.final_data_indx, :]
        last_data = pd.DataFrame(
            data_out[1:][np.newaxis, :], columns=self.ports.values(), index=np.array([data_out[0], ]))
        self.data_lock.release()
        return last_data

    def get_time(self):
        self.data_lock.acquire(True)
        t = self.data_stream[self.final_data_indx, 0].copy()
        self.data_lock.release()
        return t

    def get_next_refresh_time(self):
        if self.port_type == 'AO':
            return self.get_time() + self.controller.output_refresh_time
        else:
            return self.get_time() + self.controller.data_acquisition_period

    def wait_for_time(self, t, stop_event=None):
        """Blocks until time is surpassed or the stop event is set"""
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            if self.get_time() >= t:
                break
            time.sleep(0.01)

    def get_data(self, start_time=0, end_time=-1, wait=True, calibration=None):
        """Returns the calibrated hard-copied NI data in a numpy array

            Args:
                start_time: the starting time of data points
                end_time: the last time taken. -1 means the last time acquired
                wait (bool): should the function wait for the end_time in case end_time is longer than the current time
                calibration: which calibration to use. If the calibration is None, the objects predefined calibration is used
            Returns:
                0-th row is always time, n-th row corresponds to the n-th port in self.ports
        """
        if wait and end_time > 0:
            self.wait_for_time(end_time)
        if calibration is None:
            calibration = self.calibration
        try:
            raw_data = self.get_raw_data(
                start_time=start_time, end_time=end_time)
            result = calibration.inst2data(raw_data)
        except DangerousValue as err:
            print(self.name)
            print(err)
            result = err.data
        return result

    def prepare_interp(self, t, signal):
        """
        Prepares the date for stage_interp creating the functions which interpolate the signal to be outputted by stage_data
        """

        t -= t[0]  # absolute time doesn't matter
        # number of rate steps need to be an integer, calculated based on the amount of time
        period = t[-1]
        # get the interpolating function for the data
        functions = [lambda x, i=i, t=t, signal=signal: np.interp(
            x, t, signal[:, i], period=t[-1]) for i in range(signal.shape[1])]
        return functions, period

    def stage_interp(self, t, signal, **kwargs):
        """Stages the data for NI output. Data is in array form and is interpolated for outputs depending on the rate.
            Same kwargs as the stage_data function

        Args:
            t: 1D array, timing of the signal. The time is relative to t[0].
            signal: MxN array where N is the number of ports of the instrument.
        """
        assert self.port_type == "AO", "Only analog outputs can stage data"
        # check that the number of functions is equal to the number of ports
        assert signal.shape[1] == len(self.ports), \
            "Signal doesn't have the correct number of dimensions. First column needs to be time followed by the number of ports"

        functions, period = self.prepare_interp(t, signal)
        # stage the data using a normal stage function
        return self.stage_data(functions, period, **kwargs)

    def stage_data(self, functions, periods, autostart=True, index_reset=True, use_calibration=True,
                   calibration=None):
        """Stages the data for NI output

        Args:
            functions: Desired functions to be outputted. The functions need to take a
                time vector and return the desired output at each point of the time vector
            periods: Period of the function repetition. Can be a number or a list of numbers
            autostart: True if the output to the NI card should immediately be written, False otherwise
            index_reset: True resets the current output and starts outputting the new one immediately, False continues once the old one is finished
            use_calibration: weather or not to use the calibration, or just inputting the raw data. If the calibration is not used, that also means that the feedback is turned off.
            calibration: which calibration to use. If None, using the calibration defined in the object (unless use_calibration=False)
        """
        assert self.port_type == "AO", "Only analog outputs can stage data"
        # check that the number of functions is equal to the number of ports
        assert (callable(functions) and len(self.ports) == 1) or (len(functions) == len(self.ports)), \
            "Number of functions needs to be the same as the number of ports"
        # if periods is just one number, treat is as the same for all ports
        try:
            periods = float(periods)
            if callable(functions):
                functions = [functions]
                periods = [periods]
            else:
                periods = [periods] * len(functions)
        except TypeError:
            assert len(functions) == len(periods), "Periods needs to be a number or a list of integers the same" \
                                                   " length as the functions list"

        # make sure the outputting thread is not doing anything weird
        if self.outputting_thread.is_alive():
            self.outputting_thread_stop.set()
            self.outputting_thread.join()

        if calibration is None:
            calibration = self.calibration

        # prepare the time vector
        rate = self.controller.rate
        # number of steps needs to be an integer, so need to calculate that first
        num_steps = np.lcm.reduce([int(np.round(p * rate)) for p in periods])
        t_vector = 1 / rate * np.array(range(num_steps))
        # get the physical signal from each of the functions
        fn_eval = np.vstack([f(t_vector) for f in functions])
        assert (len(fn_eval) == len(t_vector)) or (np.shape(fn_eval)[1] == len(
            t_vector)), "The functions need to return a vector of equal length to the input t_vector!"
        # turn the signal to pandas dataframe for calibration
        physical_signal = pd.DataFrame(fn_eval.transpose(), columns=self.ports)
        physical_signal.index = t_vector
        # calibrate the physical signal to get voltages
        if use_calibration:
            # if there is no feedback, calibration should just give the signal. Otherwise, need to also pass the setpoint
            if self.feedback is None:
                signal = calibration.data2inst(physical_signal)
            else:
                signal, setpoint = calibration.data2inst(
                    physical_signal, return_setpoint=True)
                self.feedback.setpoint = setpoint
                # update feedback in the controller
                self.controller.feedback_receivers[self.name][0] = self.feedback
        else:
            signal = physical_signal
            # # if there is feedback, make sure it's set to default (always 0)
            # if self.feedback is not None:
            #     self.controller.feedback_receivers[self.name][0] = NIFeedbackController(
            #         self)
        # if the calibration returns the signal in a form of a list, then this is handled with a new thread
        # the full signal from the list is output, at the end of which only the last entry is iterated over
        # in this case, autostart=False is not supported
        if isinstance(signal, list):
            assert autostart, "If the calibration is outputting a changing signal, autostart has to be false"
            signal_out = signal[0]
            signal_repetition = signal[-1]
            t_repetition = (
                signal_out.shape[0] - signal_repetition.shape[0] / 2) / rate
        else:
            signal_out = signal
            signal_repetition = None
            t_repetition = -1
        # make sure that the data we are about to stage does not exceed 10V
        if (signal_out > 10).any(axis=None) or (signal_out < -10).any(axis=None):
            warnings.warn(
                '{} instrument input out of range!'.format(self.name))
            signal_out[signal_out > 10] = 10
            signal_out[signal_out < -10] = -10
        to_stage = {p: np.array(signal_out[p]) for p in self.ports}
        # stage the data
        self.controller.stage_data(to_stage, index_reset=index_reset)
        # start if autostart flag True
        if autostart:
            # if IO process is running, change the output
            if self.controller.IO_process.is_alive():
                start_time = self.controller.change_output()
            # if IO process not running, start it
            else:
                self.controller.start()
                start_time = 0
            # in case of a transient output, start the output thread
            if signal_repetition is not None:
                self.outputting_thread = threading.Thread(target=self.output_at_time,
                                                          args=(start_time + t_repetition, signal_repetition))
                self.outputting_thread.start()
            return start_time
        else:
            return None

    def output_at_time(self, start_time, signal, stop_event=None):
        """Waits for the start_time and outputs the signal_repetition as soon as
        that time passes without reseting the ni output index. Stop event can stop the output if triggered before the start time"""
        assert self.controller.IO_process.is_alive()
        to_stage = {p: np.array(signal[p]) for p in self.ports}
        self.controller.stage_data(to_stage, index_reset=False)
        self.wait_for_time(start_time, stop_event=stop_event)
        if not (stop_event is None or stop_event.is_set()):
            self.controller.change_output()

    def stop(self):
        """Zero all the channels"""
        if self.port_type == "AO":
            signal = [lambda x: np.zeros(len(x))] * len(self.ports)
            self.stage_data(signal, 1, autostart=True)

    def create_save_group(self, group, name=None, additional=None):
        inst_group = super().create_save_group(group, name, additional)
        inst_group.attrs['port_type'] = self.port_type
        if isinstance(self.ports, list):
            inst_group.attrs['ports'] = np.array(
                (p.encode('utf8') for p in self.ports))
        else:
            inst_group.attrs['ports'] = np.array([(key.encode('utf8'), value.encode('utf8'))
                                                  for key, value in self.ports.items()])
        return inst_group

    def save_data(self, group, data):
        # save the data
        group.create_dataset("data", data=data.reset_index().values)
        # add columns and a timestamp to attributes
        group.attrs["timestamp"] = str(datetime.now())
        group.attrs["columns"] = np.array(
            [s.encode('utf8') for s in ["t"] + list(data.columns)])
        group.attrs["0"] = "t".encode('utf8')
        for i in range(len(data.columns)):
            group.attrs[str(i + 1)] = str(data.columns[i]).encode('utf8')

    def save(self, group, name=None, start_time=0, end_time=-1, wait=True, additional=None, **kwargs):
        return super().save(group, name=name, start_time=start_time, end_time=end_time, wait=wait,
                            additional=additional, **kwargs)

    # def add_feedback_sender(self):
    #     """Adds the feedback sender to its controller with self name and the ports of the instrument.
    #     Returns the reader end of the pipe for receiving the feedback signal.
    #     """
    #     # to do this, this needs to be an input instrument
    #     assert self.port_type in {"AI", "DI"}
    #     reader = self.controller.add_feedback_sender(self.name, self.ports)
    #     return reader

    # def add_feedback_receiver(self, feedback_controller, reader):
    #     """
    #     Adds the feedback receiver to its controller with self name and the ports of the instrument.
    #     Uses the given feedback_controller as the feedback handler and saves it for reference
    #     Args:
    #         feedback_controller: NIFeedbackController class object as defined in the feedbacks
    #         reader: pipe which reads the feedback signal being sent
    #     """
    #     # to do this, this needs to be an input instrument
    #     assert self.port_type in {"AO", "DO"}
    #     self.controller.add_feedback_receiver(
    #         self.name, feedback_controller, reader)
    #     self.feedback = feedback_controller

    # def update_feedback(self):
    #     """
    #     This function updates the feedback controller in the ni controller
    #     """
    #     self.controller.update_feedback(self.name, self.feedback)

    # def turn_feedback_off(self):
    #     """
    #     This function updates the feedback controller in the ni controller with the default feedback which always gives correction 0.
    #     """
    #     basic_feedback = NIFeedbackController(self)
    #     self.update_feedback(basic_feedback)
