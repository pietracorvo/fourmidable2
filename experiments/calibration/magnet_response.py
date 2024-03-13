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


def get_nonlinear_response(moke, f, stop_event=None, period=20):
    """Gets magnet major loop by saturating -10V on inputs and saturating to
        +10 over the given period

        Args:
            moke: moke object
            f: h5py group in which to store the results
            stop_event: event which will prematuely stop the experiment
            period: time over which the rampup is done. Default is 20.
    """

    # define the relevant instruments
    magnet = moke.instruments['hexapole']
    hp = moke.instruments['hallprobe']

    # make sure the flushing time is bigger than the maximal length of data
    magnet.flushing_time = 2 * period + 5
    hp.flushing_time = 2 * period + 5
    rate = magnet.rate

    # create the group in which to save
    nlgrp = f.create_group('nonlinear_response')

    # do it for every pole
    for pole in range(3):
        pole_grp = nlgrp.create_group('pole{}'.format(pole))
        # degauss
        deGauss(moke)
        # go to fully negative on the active pole
        base_signal = signal_generation.get_const_signal(
            [0 if i != pole else -10 for i in range(3)])
        start_time = magnet.stage_data(base_signal, 0.1)
        # wait for 2 seconds for the signal to stabilise
        magnet.wait_for_time(start_time + 2)
        # apply a linear signal to 10 and stay at 10 for additional 2 seconds, and then go back
        t = np.arange(0, 2 * period + 2, 1 / rate)
        signal = np.zeros((rate * (2 * period + 2), 3))
        signal[:rate * period, pole] = np.linspace(-10, 10, rate * period)
        signal[rate * period:rate * (period + 2), pole] = 10
        signal[rate * (period + 2):, pole] = np.linspace(10,
                                                         - 10, rate * period)
        # apply the signal
        start_time = magnet.stage_interp(t, signal)
        end_time = start_time + t[-1]
        # keep checking the temperature until the end time reached
        wait_for_time_check_temp(moke, end_time)
        if stop_event is not None and stop_event.is_set():
            break

        magnet.save(pole_grp, start_time=start_time,
                    end_time=end_time, wait=False)
        hp.save(pole_grp, start_time=start_time,
                end_time=end_time, wait=False)

    # reset the outputs
    magnet.stage_data(
        signal_generation.get_zeros_signal(), 1)
    print('Non linear response collected!')


def get_frequency_response(moke, f, stop_event=None):
    """ Gets the frequency response of all three poles"""
    # define the amplitudes and frequencies of interest
    amplitude = np.linspace(0.5, 10, 20)
    frequency = 0.1 + 20 * np.linspace(0, 1, 20) ** 2
    n_loops = 3
    # get total number of loops
    total_loop = len(amplitude) * len(frequency)
    # create the saving group
    grp = f.create_group('frequency_response')
    for pole in range(3):
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
                    print('Pole {}, data point {}/{}'.format(pole
                                                             + 1, data_pt, total_loop))
                    # apply the take loop experiment
                    print('starting take loop')
                    amplitudes = [0, 0, 0]
                    amplitudes[pole] = a
                    take_sin_loop(moke, frequency=f, amplitudes=amplitudes,
                                  n_loops=n_loops, stop_event=stop_event,
                                  skip_loops=2, saving_loc=pole_grp)
    print('Frequeny response collected!')


def get_test_response(moke, f, stop_event=None):
    """ Gets the test response. One is a random signal for one pole and one a
        random signal on all three poles
    """
    # define the cutoff frequency
    cutoff_freq = 100
    n_loops = 3
    max_period = 5
    # define a period to be 5s
    period = 5
    # define the relevant instruments
    magnet = moke.instruments['hexapole']
    hp = moke.instruments['hallprobe']
    # make sure the flushing time is bigger than the maximal length of data
    magnet.flushing_time = n_loops * max_period + 5
    hp.flushing_time = n_loops * max_period + 5

    # create the saving group
    grp = f.create_group('test_response')
    for i in range(2):
        test_group = grp.create_group('test{}'.format(i))
        # get the signal generating function
        signal = signal_generation.get_random_signal(
            cutoff_freq=cutoff_freq, min_amp=1)
        if i == 0:
            # only apply on one magnet
            signal[1] = lambda x: np.zeros(len(x))
            signal[2] = lambda x: np.zeros(len(x))

        # degauss
        deGauss(moke)
        # when degaussing done, start the waveform
        start_time = magnet.stage_data(signal, period)
        # start collecting 1s later
        start_time += 1
        end_time = start_time + n_loops * period

        wait_for_time_check_temp(moke, end_time)

        print('Saving..')
        magnet.save(test_group, start_time=start_time,
                    end_time=end_time, wait=True)
        hp.save(test_group, start_time=start_time,
                end_time=end_time, wait=True)

        # reset the outputs
        magnet.stage_data(
            signal_generation.get_zeros_signal(), 1)


def get_magnet_response(moke, filename, stop_event=None):
    """ Gets the repsonse of the magnet by measuring the nonlinear response
     of the magnet, frequency response of the coils and creating some test
     sets"""

    try:
        # open the file where the data will be written
        with h5py.File(filename, 'w') as f:
            # get the nonlinear response and write to file
            print('Collecting nonlinear response')
            if not stop_event.is_set():
                get_nonlinear_response(moke, f, stop_event)
            # # get the frequency response and write to file
            # print('Collecting frequency response')
            # if not stop_event.is_set():
            #     get_frequency_response(moke, f, stop_event)
            # # get the test examples and write to file
            # print('Collecting testing signal')
            # if not stop_event.is_set():
            #     get_test_response(moke, f, stop_event)
    finally:
        # reset the outputs
        moke.instruments['hexapole'].stage_data(
            signal_generation.get_zeros_signal(), 1)
        print('Data collection completed, stopping application...')
        QApplication.quit()
        send_slack('Magnet response data collection completed!')


if __name__ == "__main__":
    from control.instruments.moke import Moke
    filename = 'magnet_currentlim_response_data.h5'
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
        moke.instruments['hallprobe'].calibration = InstrumentCalibration()

        # create the data collection thread
        stop_event = threading.Event()
        data_thread = threading.Thread(
            target=get_magnet_response, args=(moke, filename),
            kwargs={'stop_event': stop_event})
        data_thread.daemon = True
        data_thread.start()

        # start the display
        start_application(moke, [
            "hallprobe",
            "temperature",
            "hexapole"
        ])
        # once the display is closed, stop everything
        stop_event.set()
        data_thread.join()
