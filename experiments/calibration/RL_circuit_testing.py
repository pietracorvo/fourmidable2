""" The file runs a script which collets nonlinear magnet response, frequency
response of the coils and the random test signal for testing the quality of
the signal reconstruction"""

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.getcwd())

import numpy as np
from experiments.basic import (
    temp_too_high_stop, deGauss, wait_for_time_check_temp)
from experiments.take_loop import take_sin_loop
from gui.widgets.moke_docker import start_application
from control.calibration.calibrations import InstrumentCalibration
from data import signal_generation
from experiments.calibration.slack_message import send_slack

from PyQt5.QtWidgets import QApplication
import threading
import h5py


def get_dc_response(moke, f, pole, stop_event=None):
    """Applies a constant signal of a few values and measures

        Args:
            moke: moke object
            f: h5py group in which to store the results
            pole: which pole to use
            stop_event: event which will prematuely stop the experiment
    """

    # define the relevant instruments
    magnet = moke.instruments['hexapole']
    v_meas = moke.instruments['v_measurement']
    # define the delay before we start acquiring the data
    delay = 2
    acquiring_duration = 2  # how long are we acquiring for

    # create the group in which to save
    dcgrp = f.create_group('dc_response')

    # apply a constant signal
    constants = np.linspace(0.1, 3, 10)
    for i, c in enumerate(constants):
        signal_constants = np.zeros(3)
        signal_constants[pole] = c
        signal = signal_generation.get_const_signal(signal_constants)

        # create the group for the constant
        const_grp = dcgrp.create_group('const{}'.format(i))
        # apply the signal to the poles
        start_time = magnet.stage_data(signal, 1)
        start_time += delay
        end_time = start_time + delay + acquiring_duration

        # keep checking the temperature until the end time reached
        wait_for_time_check_temp(moke, end_time)
        # save into the group
        magnet.save(const_grp, start_time=start_time,
                    end_time=end_time, wait=True)
        v_meas.save(const_grp, start_time=start_time,
                    end_time=end_time, wait=True)

        if stop_event is not None and stop_event.is_set():
            break

    # reset the outputs
    magnet.stage_data(
        signal_generation.get_zeros_signal(), 1)
    print('DC response collected!')


def get_frequency_response(moke, f, pole, stop_event=None):
    """ Gets the frequency response of the given pole"""
    # define the amplitudes and frequencies of interest
    amplitude = np.linspace(0.1, 3, 10)
    frequency = 0.1 + 3 * np.linspace(0, 1, 9)
    n_loops = 10
    # get total number of loops
    total_loop = len(amplitude) * len(frequency)
    # create the saving group
    grp = f.create_group('frequency_response')
    data_pt = 0
    pole_grp = grp.create_group('pole{}'.format(pole))
    for f in frequency:
        for a in amplitude:
            # check that the stop was not triggered
            if not stop_event.is_set():
                # pause if temperature too high
                temp_too_high_stop(moke, stop_event=stop_event)
                # progress
                data_pt += 1
                print('Pole {}, data point {}/{}'.format(pole + 1, data_pt, total_loop))
                # apply the take loop experiment
                print('starting take loop')
                amplitudes = [0, 0, 0]
                amplitudes[pole] = a
                take_sin_loop(moke, frequency=f, amplitudes=amplitudes,
                              n_loops=n_loops, stop_event=stop_event,
                              skip_loops=2, saving_loc=pole_grp,
                              saving_instruments=['hexapole', 'hallprobe', 'v_measurement'])
    print('Frequeny response collected!')


def get_rl_response(moke, filename, pole, stop_event=None):
    """ Gets the repsonse of the magnet by measuring the nonlinear response
     of the magnet, frequency response of the coils and creating some test
     sets"""

    try:
        # open the file where the data will be written
        with h5py.File(filename, 'w') as f:
            # get the constant voltage response and write to file
            print('Collecting dc response')
            if not stop_event.is_set():
                get_dc_response(moke, f, pole, stop_event=stop_event)
            # get the frequency response and write to file
            print('Collecting frequency response')
            if not stop_event.is_set():
                get_frequency_response(moke, f, pole, stop_event=stop_event)
    finally:
        # reset the outputs
        moke.instruments['hexapole'].stage_data(
            signal_generation.get_zeros_signal(), 1)
        print('Data collection completed, stopping application...')
        QApplication.quit()
        send_slack('Magnet response data collection completed!')


if __name__ == "__main__":
    from control.instruments.moke import Moke

    pole = 2
    filename = 'rl_response_data_pole{}.h5'.format(pole)

    if os.path.isfile(filename):
        i = 1
        while os.path.isfile(filename + str(i)):
            i += 1
        filename = filename + str(i)

    send_slack('Will send here when done')
    print('Saving in ', filename)
    with Moke() as moke:
        # first make sure that we are using the same calibration
        # make sure that the calibration is default
        moke.instruments['hexapole'].calibration = InstrumentCalibration()
        moke.instruments['v_measurement'].calibration = InstrumentCalibration()

        # create the data collection thread
        stop_event = threading.Event()
        data_thread = threading.Thread(
            target=get_rl_response, args=(moke, filename, pole),
            kwargs={'stop_event': stop_event})
        data_thread.daemon = True
        data_thread.start()

        # start the display
        start_application(moke, [
            "v_measurement",
            "temperature",
            "hexapole"
        ])
        # once the display is closed, stop everything
        stop_event.set()
        data_thread.join()
