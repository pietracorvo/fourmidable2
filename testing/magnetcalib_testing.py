""" The file runs a script which collets nonlinear magnet response, frequency
response of the coils and the random test signal for testing the quality of
the signal reconstruction"""

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.getcwd())

import numpy as np
import pandas as pd
from control.instruments.moke import Moke
from experiments.basic import (
    temp_too_high_stop, deGauss, wait_for_time_check_temp, zero_magnet)
from experiments.take_loop import take_sin_loop
from gui.widgets.moke_docker import start_application
from control.calibration import MagnetHystCalib, InstrumentCalibration
from data import signal_generation
from data.slack_message import send_slack
import time

from PyQt5.QtGui import QApplication
import threading
import h5py


def get_frequency_response(moke, f, amplitude=None, frequency=None, stop_event=None):
    """ Gets the frequency response of all three poles"""
    # define the amplitudes and frequencies of interest
    if amplitude is None:
        amplitude = np.linspace(1, 10, 20)
    if frequency is None:
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
                    print('Pole {}, data point {}/{}'.format(pole +
                                                             1, data_pt, total_loop))
                    # apply the take loop experiment
                    print('starting take loop')
                    amplitudes = [0, 0, 0]
                    amplitudes[pole] = a
                    loop_grp = take_sin_loop(moke, frequency=f, amplitudes=amplitudes,
                                             n_loops=n_loops, stop_event=stop_event,
                                             skip_loops=2, saving_loc=pole_grp)
                    loop_grp.attrs['desired_amplitude'] = np.array(amplitudes)
                    loop_grp.attrs['desired_frequency'] = np.array(frequency)

    print('Frequeny response collected!')


def get_random_signal_response(moke, f, stop_event=None):
    """ Gets the test response. One is a random signal for one pole and one a
        random signal on all three poles
    """
    # define the cutoff frequency
    cutoff_freq = 10
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
    rate = magnet.rate

    # create the saving group
    grp = f.create_group('test_response')
    for i in range(3):
        if stop_event.is_set():
            # reset the outputs
            zero_magnet(moke)
            break
        test_group = grp.create_group('test{}'.format(i))
        # get the signal generating function
        signal = signal_generation.get_random_signal(
            cutoff_freq=cutoff_freq, min_amp=5, max_amp=40)
        if i == 0:
            # only apply on one magnet
            signal[1] = lambda x: np.zeros(len(x))
            signal[2] = lambda x: np.zeros(len(x))
        # create the desired signal
        signal_wanted = np.zeros((period * rate, 4))
        signal_wanted[:, 0] = np.arange(0, period, 1 / rate)
        for i in range(3):
            signal_wanted[:, i + 1] = signal[i](signal_wanted[:, 0])

        # degauss
        deGauss(moke)
        # when degaussing done, start the waveform
        start_time = magnet.stage_interp(signal_wanted[:, 0], signal_wanted[:, 1:])
        end_time = start_time + n_loops * period

        wait_for_time_check_temp(moke, end_time)

        print('Saving..')
        magnet.save(test_group, start_time=start_time,
                    end_time=end_time, wait=True)
        hp.save(test_group, start_time=start_time,
                end_time=end_time, wait=True)
        test_group.create_dataset("desired_output", data=signal_wanted)

        # reset the outputs
        zero_magnet(moke)
        time.sleep(1)


def get_magnet_response(moke, filename, stop_event=None):
    """ Gets the repsonse of the magnet for comparison of calibration by applying a random signal, as well as a loop"""

    try:
        # open the file where the data will be written
        with h5py.File(filename, 'w') as f:
            # get the frequency response and write to file
            print('Collecting frequency response')
            # amplitude = [10,]
            # frequency = [1,]
            # amplitude = [2, 4, 8, 16, 32]
            # frequency = [0.5, 1, 2, 10, 20]
            amplitude = np.linspace(2, 40, 10) / 27.26
            frequency = [0.5, 1, 2, 5, 8, 10]
            if not stop_event.is_set():
                get_frequency_response(moke, f,
                                       amplitude=amplitude, frequency=frequency, stop_event=stop_event)
            if not stop_event.is_set():
                # get the test examples and write to file
                print('Collecting testing signal')
                get_random_signal_response(moke, f, stop_event)
    finally:
        # reset the outputs
        moke.instruments['hexapole'].stage_data(
            signal_generation.get_zeros_signal(), 1)
        print('Data collection completed, stopping application...')
        QApplication.quit()
        send_slack('Magnet response data collection completed!')

if __name__ == "__main__":
    filename = 'magnet_calibration_test'
    ext = '.h5'
    calib_file = r'C:\Users\user\Documents\Python\MOKEpy\data\magnet_response_parameters_hyst.p'
    if os.path.isfile(filename + ext):
        i = 1
        while os.path.isfile(filename + str(i) + ext):
            i += 1
        filename += str(i)
    filename += ext
    print('Saving in ', filename)
    send_slack('Will send here when done')
    with Moke() as moke:
        # first make sure that we are using the same calibration

        # make sure that we are using the correct calibration
        moke.instruments['hallprobe'].calibration = InstrumentCalibration()
        # moke.instruments['hexapole'].calibration = MagnetHystCalib(calib_file, moke.instruments['hallprobe'])

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
