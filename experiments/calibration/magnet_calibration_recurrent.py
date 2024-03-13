import numpy as np
import pandas as pd

if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.getcwd())
from experiments.basic import temp_too_high, deGauss
import threading
from data import signal_generation
from control.calibration.calibrations import InstrumentCalibration

from gui.widgets.moke_docker import MokeDocker
import sys
from PyQt5.QtWidgets import *
import traceback
import time
import h5py


def loop_worker(mk, stop_event, cutoff_freq=100, n_loops=3, skip_loops=3, max_period=1, min_period=0.1, n_data=None):
    try:
        # define the relevant instruments
        magnet = mk.instruments['hexapole']
        hp = mk.instruments['hallprobe']
        # make sure that the calibration is default
        magnet.calibration = InstrumentCalibration()
        hp.calibration = InstrumentCalibration()
        # make sure the flushing time is bigger than the maximal length of data
        magnet.flushing_time = n_loops * max_period + 5
        hp.flushing_time = n_loops * max_period + 5

        # get the signal generating function
        signal = signal_generation.get_random_signal(cutoff_freq=cutoff_freq)

        # open a file in which to write
        filename = 'MagCalib_' + time.strftime("%Y%m%d-%H%M%S") + '.h5'
        data_point_number = 1
        with h5py.File(filename, 'w') as f:
            i = 0
            while True:
                i += 1
                if n_data is not None and i > n_data:
                    break
                print('Data ', i)
                # create a random period (but well defined in rate)
                period = np.round(
                    min_period + (np.random.rand() * (max_period - min_period)), 4)
                print('Period: ', period)
                # create the group in which to put loops
                grp = f.create_group('data' + str(i))
                grp.attrs['period'] = period
                grp.attrs['cutoff_freq'] = cutoff_freq
                grp.attrs['n_loops'] = n_loops
                grp.attrs['skip_loops'] = skip_loops

                # degaussing
                deGauss(mk)
                # allow for cooldown if the temperature is too high
                if temp_too_high(mk, 55):
                    while temp_too_high(mk, 35):
                        if (stop_event is not None) and (stop_event.is_set()):
                            break
                        print(
                            'Temperature too high, will wait until it goes below ', 35)
                        time.sleep(5)
                        continue
                    if (stop_event is not None) and (stop_event.is_set()):
                        break

                # when degaussing done, start the waveform
                start_time = magnet.stage_data(signal, period)
                # the start time is when magnet starts outputting plus skipped loops
                start_time += skip_loops * period
                end_time = start_time + n_loops * period
                print('Wait time: ', end_time - magnet.get_time())
                # wait for time while listening to the stop event
                while True:
                    time.sleep(0.1)
                    if ((stop_event is not None) and (stop_event.is_set())) or (magnet.get_time() >= end_time):
                        break
                if (stop_event is not None) and (stop_event.is_set()):
                    break
                # save the relevant instruments
                print('Saving..')
                magnet.save(grp, start_time=start_time,
                            end_time=end_time, wait=True)
                hp.save(grp, start_time=start_time,
                        end_time=end_time, wait=True)

            # reset the outputs
            magnet.stage_data(
                signal_generation.get_zeros_signal(), 1, autostart=True)
            print('Experiment finished')
    except:
        traceback.print_exc()
    print('Finished!')


# applies the take_loop experiment on the given list of frequencies and amplitudes
if __name__ == "__main__":
    from control.instruments.moke import Moke
    # define frequency and amplitude
    cutoff_freq = 100
    n_loops = 3
    skip_loops = 2
    n_data = 10

    # import matplotlib.pyplot as plt
    # rate = 10000
    # t = np.arange(0, np.random.rand() * 5, 1 / rate)
    # plt.plot(t, get_random_signal(t, cutoff_freq))
    # plt.show(block=True)
    # sys.exit()
    # initialise the moke
    with Moke() as mk:
        # prepare the thread and start it
        stop_event = threading.Event()
        # NEED TO ADD KEYWORDS
        saving_thread = threading.Thread(
            target=loop_worker, args=(mk, stop_event),
            kwargs={'cutoff_freq': cutoff_freq, 'n_loops': n_loops, 'skip_loops': skip_loops, 'n_data': n_data})
        saving_thread.daemon = True
        saving_thread.start()

        # start plotting
        app = QApplication(sys.argv)
        dock_list = [
            "hallprobe",
            "temperature",
            "hexapole"
        ]
        aw = MokeDocker(mk, dock_list=dock_list)
        aw.show()
        app.exec_()

        stop_event.set()
        saving_thread.join()
