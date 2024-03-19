import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.getcwd())
from control.instruments.moke import Moke
import threading
from control.calibration.calibrations import InstrumentCalibration
import h5py
from scipy.stats import binned_statistic
from gui.widgets.moke_docker import start_application
from experiments.take_loop import take_sin_loop, take_loop
from data.signal_generation import get_sin_fun, get_zeros_signal


def combine_fun(x, amplitudes, frequencies):
    # initialise with zeros everywhere
    result = np.zeros(len(x))
    for a, f in zip(amplitudes, frequencies):
        fun = get_sin_fun(a, 1/f, 0)
        result += fun(x)
    return result


def start_test(moke, filename, amplitudes=[2, 6], frequencies=[1, 5], stop_event=None):
    """First runs individual amplitude-frequency pairs in order and then all of them together"""
    assert len(amplitudes) == len(frequencies)
    # define the relevant instruments
    magnet = moke.instruments['hexapole']
    hp = moke.instruments['hallprobe']
    rate = magnet.rate
    # make sure that the calibration is default
    magnet.calibration = InstrumentCalibration()
    hp.calibration = InstrumentCalibration()

    # define combined signal
    periods = np.array([1/f for f in frequencies])
    combined_period = rate*np.prod(periods) / np.gcd.reduce(np.round(periods*rate).astype(int))
    combined_signal = np.zeros((int(combined_period*rate), 4))
    combined_signal[:, 0] = np.arange(0, combined_period, 1/rate)
    combined_signal[:, 1] = combine_fun(combined_signal[:, 0], amplitudes, frequencies)
    # combined_signal = [lambda x: combine_fun(x, amplitudes, frequencies),
    #                    lambda x: np.zeros(len(x)),
    #                    lambda x: np.zeros(len(x))]

    with h5py.File(filename, 'w') as file:
        # when all the sin loops done, make a set of loops with the combination of frequencies
        combined_grp = file.create_group('combined')
        take_loop(moke, 1/combined_period, signal=combined_signal, n_loops=3, skip_loops=2,
                  stop_event=stop_event, saving_loc=combined_grp, saving_instruments=['hallprobe', 'hexapole'])
        # take each loop separately
        for i, (f, a) in enumerate(zip(frequencies, amplitudes)):
            grp = file.create_group('component' + str(i))
            # take a sin loop with the given amp and freq
            take_sin_loop(moke, f, (a, 0, 0), n_loops=3, skip_loops=2, stop_event=stop_event, saving_loc=grp)



if __name__ == "__main__":
    filename = 'coil_linearity_test_highF.h5'

    with Moke() as mk:
        stop_event = threading.Event()
        test_thread = threading.Thread(target=start_test, args=(mk, filename),
                                       kwargs={"amplitudes": [1, 6], "frequencies": [1, 10],
                                               "stop_event": stop_event})
        test_thread.daemon = True
        test_thread.start()

        start_application(mk, [
            "hallprobe",
            "hexapole",
            "temperature"
        ])
        stop_event.set()
        test_thread.join()
