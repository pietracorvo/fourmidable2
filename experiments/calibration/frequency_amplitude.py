import pandas as pd
import numpy as np
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from gui.widgets.moke_docker import MokeDocker, start_application
from experiments.take_loop import take_sin_loop
from data.signal_generation import get_zeros_signal
from experiments.basic import temp_too_high_stop
from control.calibration.calibrations import InstrumentCalibration
import threading

from gui.widgets.canvas import DynamicMokePlot
import sys
from PyQt5.QtWidgets import *
import traceback
import time


def loop_worker(mk, amplitude, frequency, n_loops, stop_event):
    # get the useful instruments
    magnet = mk.instruments['hexapole']
    hp = mk.instruments['hallprobe']
    # make sure that the calibration is not getting in the way
    magnet.calibration = InstrumentCalibration()
    hp.calibration = InstrumentCalibration()
    # get total number of loops
    total_loop = len(amplitude) * len(frequency)
    i = 0
    for a in amplitude:
        for f in frequency:
            # check that the stop was not triggered
            if not stop_event.is_set():
                # pause if temperature too high
                temp_too_high_stop(mk, stop_event=stop_event)
                # progress
                i += 1
                print('Data ', i, '/', total_loop)
                try:
                    # apply the take loop experiment
                    print('starting take loop')
                    take_sin_loop(mk, frequency=f, amplitudes=(a, 0, 0),
                                  n_loops=n_loops, stop_event=stop_event, skip_loops=2)
                except:
                    traceback.print_exc()
    print('Finished!')


# applies the take_loop experiment on the given list of frequencies and amplitudes
if __name__ == "__main__":
    from control.instruments.moke import Moke
    print('hello')
    # define frequency and amplitude
    amplitude = np.linspace(1, 10, 20)
    frequency = 0.1 + 20 * np.linspace(0, 1, 20)**2
    # amplitude = np.linspace(1, 10, 10)
    # frequency = [0.1, 0.5, 1, 2, 2.5, 4, 5, 8,
    #              10, 16, 20, 25, 40, 50, 62.5, 80, 100]
    n_loops = 3

    n_total = len(amplitude * len(frequency))
    estimated_time = np.sum(
        n_total * 5 + 1 / np.array(frequency) * (n_loops + 2) * len(amplitude))
    print('Estimated time: ', int(estimated_time / 60), 'min')

    # initialise the moke
    with Moke() as mk:
        # prepare the thread and start it
        stop_event = threading.Event()
        saving_thread = threading.Thread(target=loop_worker, args=(
            mk, amplitude, frequency, n_loops, stop_event))
        saving_thread.daemon = True
        saving_thread.start()

        start_application(mk, [
            "hallprobe",
            "temperature",
            "hexapole"
        ])
        stop_event.set()
        saving_thread.join()
