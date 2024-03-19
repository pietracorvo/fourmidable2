""" The file runs a script which collets nonlinear magnet response, frequency
response of the coils and the random test signal for testing the quality of
the signal reconstruction"""

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.getcwd())

import numpy as np
from control.instruments.moke import Moke
from experiments.basic import (
    temp_too_high_stop, deGauss, wait_for_time_check_temp, zero_magnet)
from experiments.take_loop import take_sin_loop
from gui.widgets.moke_docker import start_application
from data import signal_generation
import time

import threading
import traceback


def test_feedback(moke, stop_event=None):
    """
    Runs a few simple tests for the feedback.
    """
    try:
        magnet = moke.instruments['hexapole']
        # check that we can zero the signal
        print('Zeroing the signal')
        zero_magnet(moke)
        if stop_event.is_set():
            return
        time.sleep(2)
        # # check that we can degauss
        # print('Degaussing...')
        # deGauss(moke)
        # if stop_event.is_set():
        #     return
        # time.sleep(2)
        # check what happens if we apply a constant signal (aim for 10mT)
        field = 20
        for i, pole in enumerate(['A', 'B', 'C']):
            print('Applying {} mT to pole {}'.format(field, pole))
            constants = np.zeros(3)
            constants[i] = field
            if stop_event.is_set():
                return
            magnet.stage_data(
                signal_generation.get_const_signal(constants), 1)
            time.sleep(5)
        # check that we can apply sin signals (again amplitude 10mT)
        for i, pole in enumerate(['A', 'B', 'C']):
            print('Applying sin signal with amplitude {} mT to pole {}'.format(
                field, pole))
            if stop_event.is_set():
                return
            amplitudes = np.zeros(3)
            amplitudes[i] = field
            frequency = 1
            take_sin_loop(moke, frequency=frequency, amplitudes=amplitudes,
                          n_loops=5, stop_event=stop_event, save=False)
        print('Testing finished with no errors!')
    except:
        traceback.print_exc()
        print('Thread exited with error!')


if __name__ == "__main__":
    with Moke() as moke:
        # create the thread for testing the data
        stop_event = threading.Event()
        data_thread = threading.Thread(
            target=test_feedback, args=(moke,),
            kwargs={'stop_event': stop_event})
        data_thread.daemon = True
        data_thread.start()

        # start the display
        start_application(moke, [
            "hallprobe",
            "hexapole",
            "temperature"
        ])
        # once the display is closed, stop everything
        stop_event.set()
        data_thread.join()
