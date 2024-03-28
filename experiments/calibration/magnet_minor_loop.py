import numpy as np
import matplotlib.pyplot as plt

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from experiments.basic import temp_too_high_stop, deGauss
from gui.widgets.moke_docker import MokeDocker, start_application
from control.calibration.calibrations import InstrumentCalibration
from data import signal_generation

from PyQt5.QtWidgets import QApplication
import threading
import h5py
import time


def get_minor_loops(moke, filename, period=10, step=1, stop_event=None):
    """Gets minor loops starting from -10V on inputs and saturating to +10 with given step and period. 
    It does it one pole at a time and stores everything to one file
    """

    # define the relevant instruments
    magnet = mk.instruments['hexapole']
    hp = mk.instruments['hallprobe']
    # make sure that the calibration is default
    magnet.calibration = InstrumentCalibration()
    hp.calibration = InstrumentCalibration()
    # make sure the flushing time is bigger than the maximal length of data
    magnet.flushing_time = period + 5
    hp.flushing_time = period + 5
    rate = magnet.rate

    with h5py.File(filename, 'w') as f:
        # do it for every pole
        for pole in range(3):
            pole_grp = f.create_group('pole{}'.format(pole))
            # degauss
            deGauss(mk)
            saturation_amplitude = 8
            # go to fully negative on the active pole
            base_signal = signal_generation.get_const_signal(
                [0 if i != pole else -saturation_amplitude for i in range(3)])
            start_time = magnet.stage_data(base_signal, 0.1)
            # wait for 1 second for the signal to stabilise
            magnet.wait_for_time(start_time + 1)
            # go through all the minor loops in steps
            for j, amp in enumerate(np.arange(step, 2*saturation_amplitude + step, step)):
                # break if stop event triggered
                if stop_event is not None and stop_event.is_set():
                    break
                # check if the temperature is too hot. If so, immediately put the current to 0 and wait
                temp_too_high_stop(mk, max_temp=50)
                # when ready to continue, stage the base signal and wait 1 second to make sure you are back at it
                magnet.stage_data(base_signal, 3)
                time.sleep(1)
                if (stop_event is not None) and (stop_event.is_set()):
                    break
                # get the zero signal for all apart from the active pole
                t = np.arange(0, period + 2, 1 / rate)
                signal = np.zeros((int(rate * (period + 2)), 3))
                signal[:int(rate * period), pole] = -saturation_amplitude + amp / 2 * \
                    (1 - np.cos(np.pi * 2 * t[:int(rate * period)] / period)
                     )  # this is the signal going up to the desired value and back
                # stage 10s after it comes back so that there is no going back up while saving
                signal[int(rate * period):, pole] = -saturation_amplitude

                # apply the signal
                start_time = magnet.stage_interp(t, signal)
                end_time = start_time + period
                # save the result
                grp = pole_grp.create_group('step{}'.format(j))

                magnet.save(grp, start_time=start_time,
                            end_time=end_time, wait=True)
                hp.save(grp, start_time=start_time,
                        end_time=end_time, wait=True)
                # bighp.save(grp, start_time=start_time,
                #            end_time=end_time, wait=True)
            if stop_event is not None and stop_event.is_set():
                break

    # reset the outputs
    magnet.stage_data(
        signal_generation.get_zeros_signal(), 1)
    print('Experiment finished')

    QApplication.quit()


if __name__ == "__main__":
    from control.instruments.moke import Moke
    filename = 'hex_minor_Ichannel.h5'
    #period = 10
    period = 5
    step = 1

    with Moke() as mk:
        stop_event = threading.Event()
        test_thread = threading.Thread(
            target=get_minor_loops, args=(mk, filename), kwargs={'stop_event': stop_event, 'period': period, 'step': step})
        test_thread.daemon = True
        test_thread.start()

        start_application(mk, [
            "hallprobe",
            "temperature",
            "hexapole"
        ])
        stop_event.set()
        test_thread.join()
