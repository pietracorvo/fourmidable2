import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from control.instruments.moke import Moke
from experiments.basic import temp_too_high, deGauss
from gui.widgets.moke_docker import MokeDocker
from PyQt5.QtGui import QApplication
import threading
from control.calibration.calibrations import InstrumentCalibration
from data import signal_generation
import h5py
from scipy.stats import binned_statistic
from gui.widgets.moke_docker import start_application


def start_test(moke, filename, min_period=0.5, max_period=2, n_loops=3):
    """Runs a random signal with the given calibration and measures for num_periods"""
    # get a random period
    period = np.round(
        min_period + (np.random.rand() * (max_period - min_period)), 4)
    print('Period {}s'.format(period))

    # define the relevant instruments
    magnet = mk.instruments['hexapole']
    hp = mk.instruments['hallprobe']
    # make sure that the calibration is default
    # magnet.calibration = InstrumentCalibration()
    # hp.calibration = InstrumentCalibration()
    # make sure the flushing time is bigger than the maximal length of data
    magnet.flushing_time = n_loops * max_period + 5
    hp.flushing_time = n_loops * max_period + 5
    # get the rate
    rate = magnet.rate

    # get the signal generating function and the values for the given rate
    signal = signal_generation.get_sin_signal([50, 0, 0], period)
    t = 1 / rate * np.array(range(int(np.round(n_loops * period * rate))))
    signal_vals = np.hstack((t[:, np.newaxis], np.array(
        [signal[i](t) for i in range(3)]).T))

    # degauss
    deGauss(mk)
    # when degaussing done, start the waveform
    start_time = magnet.stage_data(signal, period)
    end_time = start_time + period * n_loops
    # save the relevant instruments
    print('Saving..')
    with h5py.File(filename, 'w') as f:
        # grp = f.create_group('data')
        grp = f.create_group('wanted_signal')
        grp.create_dataset("data", data=signal_vals)
        magnet.save(f, start_time=start_time,
                    end_time=end_time, wait=True)
        hp.save(f, start_time=start_time,
                end_time=end_time, wait=True)

    # reset the outputs
    magnet.stage_data(
        signal_generation.get_zeros_signal(), 1, autostart=True)
    print('Experiment finished')

    QApplication.quit()


if __name__ == "__main__":
    filename = 'calib_test.h5'

    with Moke() as mk:
        test_thread = threading.Thread(target=start_test, args=(mk, filename))
        test_thread.daemon = True
        test_thread.start()

        start_application(mk, [
            "hallprobe",
            # "temperature",
            "hexapole"
        ])

        test_thread.join()

        # see how well the procedure worked
        with h5py.File(filename, 'r') as f:
            hp = f.get('hallprobe/data')[:, :]
            hx = f.get('hexapole/data')[:, :]
            signal_vals = f.get('wanted_signal/data')[:, :]

        hp_filtered = binned_statistic(hp[:, 0], hp.T, 'mean', bins=np.arange(
            hp[0, 0], hp[-1, 0], 1 / 100)).statistic.T
        plt.plot(hp_filtered[:, 0], hp_filtered[:, 1], label='True signal')
        plt.plot(signal_vals[:, 0] + hp_filtered[0, 0],
                 signal_vals[:, 1], label='Wanted signal')
        plt.legend()

        plt.xlabel('t[s]')
        plt.ylabel('Bx[mT]')
        plt.show(block=True)
