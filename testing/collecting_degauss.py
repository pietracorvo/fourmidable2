import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from control.instruments.moke import Moke
from experiments.basic import temp_too_high_stop, deGauss
from gui.widgets.moke_docker import MokeDocker, start_application
from control.calibration.calibrations import InstrumentCalibration
from data import signal_generation

from PyQt5.QtWidgets import QApplication
import threading
import h5py
import time


def collect_degauss(moke, filename):
    # define the relevant instruments
    magnet = mk.instruments['hexapole']
    hp = mk.instruments['hallprobe']
    # make sure that the calibration is default
    magnet.calibration = InstrumentCalibration()
    hp.calibration = InstrumentCalibration()
    # make sure the flushing time is bigger than the maximal length of data
    magnet.flushing_time = 10
    hp.flushing_time = 10

    with h5py.File(filename, 'w') as f:
        # do it for every pole
        grp = f.create_group('degaussing')
        # degauss
        start_time = magnet.get_time()
        deGauss(mk)
        end_time = magnet.get_time()
        magnet.save(grp, start_time=start_time, end_time=end_time)
        hp.save(grp, start_time=start_time, end_time=end_time)

    # reset the outputs
    magnet.stage_data(
        signal_generation.get_zeros_signal(), 1)
    print('Experiment finished')

    QApplication.quit()


if __name__ == "__main__":
    filename = 'degauss_signal.h5'

    with Moke() as mk:
        stop_event = threading.Event()
        test_thread = threading.Thread(
            target=collect_degauss, args=(mk, filename))
        test_thread.daemon = True
        test_thread.start()

        start_application(mk, [
            "hallprobe",
            "temperature",
            "hexapole"
        ])
        stop_event.set()
        test_thread.join()
