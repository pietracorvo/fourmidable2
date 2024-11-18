import warnings
import numpy as np
import traceback
import time
import h5py
from scipy import signal
import data.signal_generation as signal_generation
from .basic import deGauss
import os
from experiments.basic import magnet_loop_tuning, zero_magnet
import threading


def take_loop(moke, signal=None, period=1, n_loops=5,
              skip_loops=0, stop_event=None, data_callback=None, save=True,
              degauss=True, min_saving_period=1,
              saving_instruments=None,
              saving_loc=None,
              tune_loop=False):
    """Degausses and then sets a signal to the hexapole. Records a loop after every recording_period

    Args:
        moke: handle to moke object
        signal: which signal to input to hexapole. It can be either a function or a numpy array. In the latter case,
            the first column needs to be time
        n_loops: the number of loops required. If set negative or 0, keeps going until the stop event signal is True
        stop_event: Setting to True stops the loop
        skip_loops: number of loops to skip before the data acquisition starts
        data_callback: function that is called on every loop (e.g. for plotting)
        save (bool): weather to save data or not
        degauss (bool): weather to degauss or not
        min_saving_period: minimum amount of time between saves. You can make saving faster, but at some point the
                            computer won't be able to write data to disk in separate batches fast enough
        saving_instruments: list of instruments names which to save. By default  ['hexapole', 'hallprobe', 'wollaston1', 'wollaston2']
        saving_loc (None, str, group): file in which to save data. If None, a new file is created with default name. If str,
            A file is created at a given path. If group, the loops are saved in the given h5py group
        tune_loop : weather or not to start the tuning thread to improve the loop. For this, moke has to have the loop_tuning parameters defined in the settings file
    """
    # if stop event set, immediately return
    if (stop_event is not None) and (stop_event.is_set()):
        return None
    # get instruments which we are going to use for convenience
    magnet = moke.instruments['hexapole']

    # check that the signal is valid and prepare it for output
    if signal is None:
        signal = signal_generation.get_zeros_signal()
    elif isinstance(signal, np.ndarray):
        assert signal.shape[1] == 4, "Need 4 columns!"
        if period is not None:
            warnings.warn(
                'If numpy array passed to loop, the period is automatically calculated')
        # make sure that the first column is time
        assert np.all(signal[1:, 0] > signal[:-1, 0]), "First column needs to be time and be " \
            "monotonically increasing!"
        # create functions which interpolate the passed array signal. This is necessary for loop tuning and other functions down the line.
        signal, period = magnet.prepare_interp(
            signal[:, 0], signal[:, 1:])
    else:
        assert all([callable(s) for s in signal]), 'Unrecognised signal input'

    if saving_instruments is None:
        saving_instruments = ['hexapole',
                              'hallprobe', 'wollaston1', 'wollaston2', 'bighall_fields']
        saving_instruments = [
            s for s in saving_instruments if s in moke.instruments]

    # set the flushing time to be appropriate
    for inst in saving_instruments:
        moke.instruments[inst].flushing_time = np.max([period + 1, 10])

    time.sleep(0.1)
    # calculate the save period. It is integer the smallest number of periods which is bigger than the save period. Unless that number is smaller than the number of loops
    # Note: there has to be a minimal saving period otherwise the saving will not be able to keep up with the acquisition.
    # For future reference, this can be pushed down to 0.1s. Especially if the callbacks are done less frequently (have separate callback time)
    n_periods = np.ceil(min_saving_period / period).astype(int)
    save_period = n_periods * period
    if n_loops > 0 and save_period > n_loops * period:
        save_period = n_loops * period

    # degauss and zeros after
    if degauss:
        deGauss(moke)

    f = None
    tuning_thread = None
    # create a file to save the experiment in
    try:
        if save:
            # if already passed the group, no need to create anything
            if not isinstance(saving_loc, h5py.Group):
                f = get_save_handle(saving_loc)
            else:
                f = saving_loc
            # save the stage location and camera images if they exist
            #for key in ['stage', 'camera1', 'camera2']:
                #if key in moke.instruments:
            #moke.instruments['stage'].save(f)
            grp = create_loops_group(f)
            grp.attrs['period'] = period
            grp.attrs['loops_per_data'] = n_periods
        else:
            # start saving group as None for later return
            grp = None
        start_time, tuning_thread, tune_stop = start_signal(
            moke, signal, period, tune_loop=tune_loop)
        # run periods
        i = 0
        while True:
            i += 1
            # check if the number of loops was reached. If number of loops negative, keeps going until the event set
            if i * n_periods > n_loops + skip_loops and n_loops >= 1:
                break
            print('Loop ', i * n_periods)

            # get the end time and wait for it
            end_time = start_time + save_period

            lagging = wait_for_time(magnet, stop_event, end_time)
            if lagging and magnet.get_time() > end_time + period:
                print(
                    'Lagging! Experiment frequency too fast to keep up with for long.')
                print('Lag time: ', magnet.get_time() - end_time)
            if (stop_event is not None) and (stop_event.is_set()):
                break

            if i > skip_loops:
                if save:
                    # save all the instruments
                    inst_grp = grp.create_group('data' + str(i))
                    save_instruments(moke, inst_grp, saving_instruments,
                                     start_time, end_time)
                if data_callback is not None:
                    send_data_callback(
                        moke, data_callback, saving_instruments, start_time, end_time)
            start_time += save_period
    finally:
        # close, unless h5py object passed, in which case the outer process has to deal with that
        if save and not isinstance(saving_loc, h5py.Group):
            f.file.close()

        if tuning_thread is not None and tuning_thread.is_alive():
            tune_stop.set()
            tuning_thread.join(timeout=5)
            if tuning_thread.is_alive():
                print('Did not manage to stop the tuning thread!!')
                print(tune_stop.is_set())
                print(tuning_thread)
                raise Exception('Could not stop the thread')
        zero_magnet(moke)
        print('Zeroed the magnet')

    print('Experiment finished')

    return grp


###################################################################################################

def start_signal(moke, signal, period, tune_loop=False):
    # define the tune stop event if not defined already

    magnet = moke.instruments['hexapole']
    # when degaussing done, start the sin-wave
    start_time = magnet.stage_data(signal, period, autostart=True)

    # start loop tuning if wanted
    if tune_loop:
        tune_stop = threading.Event()
        # start tuning after two periods
        tune_start = start_time + 2 * period
        tuning_thread = threading.Thread(target=magnet_loop_tuning,
                                         args=(moke, signal, period,
                                               tune_start, tune_stop))
        tuning_thread.daemon = True
        tuning_thread.start()
    else:
        tune_stop = None
        tuning_thread = None
    return start_time, tuning_thread, tune_stop


def get_save_handle(saving_loc):
    # check if the saving_loc is None, path or group, proceed accordingly
    default_filename = 'LoopTaking_' + \
               time.strftime("%Y%m%d-%H%M%S") + '.h5'
    if saving_loc is None:
        filepath = os.path.join(os.getcwd(), default_filename)
        print('Saving to ', filepath)
        f = h5py.File(filepath, 'a')
    elif isinstance(saving_loc, str):
        if os.path.isdir(saving_loc):
            filepath = os.path.join(os.path.abspath(saving_loc), default_filename)
        else:
            filepath = saving_loc
        print('Saving to ', filepath)
        f = h5py.File(filepath, 'a')
    else:
        raise Exception('Saving location file type not recognised!')
    return f


def create_loops_group(f):
    # create the group in which to put loops
    # check which groups exist so as to not overwrite
    i = 1
    grp_name = 'loops'
    existing_names = set(f.keys())
    while grp_name in existing_names:
        grp_name = 'loops' + str(i)
        i += 1
    grp = f.create_group(grp_name)

    return grp


def wait_for_time(time_instrument, stop_event, end_time):
    # wait for time while listening to the stop event
    lagging = True
    while True:
        time.sleep(0.001)
        if ((stop_event is not None) and (stop_event.is_set())) or (
                time_instrument.get_time() >= end_time):
            break
        else:
            lagging = False
    return lagging


def save_instruments(moke, inst_grp, saving_instruments, start_time, end_time):
    for inst in saving_instruments:
        moke.instruments[inst].save(inst_grp, start_time=start_time,
                                    end_time=end_time)

def append_save_instruments(moke, grp, saving_instruments, start_time, end_time):
    """
    Same like save_instruments, but appends data if group already present.
    """
    for inst in saving_instruments:
        try:
            save_instruments(moke, grp, [inst], start_time, end_time)
        except ValueError:
            # append if group already present
            data = moke.instruments[inst].get_data(start_time=start_time, end_time=end_time)
            data = data.reset_index()
            data = data.values
            old_shape = grp[inst]['data'].shape
            new_shape = (old_shape[0] + data.shape[0], old_shape[1])
            grp[inst]['data'].resize(new_shape)
            grp[inst]['data'][old_shape[0]:,:] = data

def send_data_callback(moke, data_callback, saving_instruments, start_time, end_time):
    inst_data = dict()
    for inst in saving_instruments:
        inst_data[inst] = moke.instruments[inst].get_data(
            start_time=start_time, end_time=end_time)
    data_callback(inst_data)


def take_sin_loop(moke, frequency=1, amplitudes=(1, 1, 1), phases=(0, 0, 0), offsets=(0, 0, 0), n_loops=5,
                  skip_loops=0, stop_event=None, data_callback=None, degauss=True, min_saving_period=1,
                  saving_loc=None, saving_instruments=None, tune_loop=False, save=True):
    """Degausses and then sets a sin-wave with given periods and amplitudes. Records a loop after every recording_period.

    Args:
        moke: handle to moke object
        frequency: the frequency of the loop
        amplitudes: amplitude of the signal per magnet
        phases: phase of the signal per magnet (in degrees)
        n_loops: the number of loops required. If set negative or 0, keeps going until the stop event signal is True
        stop_event: Setting to True stops the loop
        skip_loops: number of loops to skip before the data acquisition starts
        data_callback: function that is called on every loop (e.g. for plotting)
        save (bool): weather to save data or not
        degauss (bool): weather to degauss or not
        min_saving_period: minimum amount of time between saves. You can make saving faster, but at some point the
                            computer won't be able to write data to disk in separate batches fast enough
        saving_loc (None, str, group): file in which to save data. If None, a new file is created with default name. If str,
            A file is created at a given path. If group, the loops are saved in the given h5py group
        saving_instruments (None, list(str)): which instruments to save. If none will use default: ['hexapole', 'hallprobe', 'wollaston1', 'wollaston2']
        tune_loop : weather or not to start the tuning thread to improve the loop. For this, moke has to have the loop_tuning parameters defined in the settings file
    """

    # prepare the output functions
    period = 1 / frequency
    signal = signal_generation.get_sin_signal(
        amplitudes, [period] * 3, phases=phases, offsets=offsets)

    try:
        # create your own save group so that additional info can be passed
        if save:
            # if already passed the group, no need to create anything
            if not isinstance(saving_loc, h5py.Group):
                grp = get_save_handle(saving_loc)
            else:
                grp = saving_loc
        else:
            grp = None

        grp = take_loop(moke, signal=signal, period=period, n_loops=n_loops,
                        skip_loops=skip_loops, stop_event=stop_event, data_callback=data_callback, save=save,
                        degauss=degauss, min_saving_period=min_saving_period,
                        saving_instruments=saving_instruments,
                        saving_loc=grp,
                        tune_loop=tune_loop)
        grp.attrs['amplitudes'] = amplitudes
    finally:
        # close, unless h5py object passed, in which case the outer process has to deal with that
        if save and not isinstance(saving_loc, h5py.Group):
            f.file.close()
    return grp
