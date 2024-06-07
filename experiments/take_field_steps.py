import time
from .basic import deGauss
from experiments.basic import zero_magnet
import threading
import numpy as np


def take_steps(moke, signals, stop_event=None):
    """
    Degauss and then use the pid to sequentially apply constant fields.

    Args:
        moke: handle to moke object
        signals: Nx3 array of field points for the 3 magnets that are sequentially approached by PID
        stop_event: Setting to True stops the loop
    """

    # function that is run in a thread
    def run_steps_experiment(moke, signals, stop_event):

        hp = moke.instruments['hallprobe']
        hexapole = moke.instruments['hexapole']

        Kp = 0.3
        # for ID in PID, seems not to work
        # Ki = 0.5
        # Kd = 0.5
        nb_points_used = 500
        stop_criterion = 0.3 / 27.26  # noise less than 0.3mT

        deGauss(moke)

        for signal in signals:
            # previous_error = np.zeros((nb_points_used, 3))
            # integral = np.zeros((nb_points_used, 3))
            while True:
                if (stop_event is not None) and (stop_event.is_set()):
                    zero_magnet(moke)
                    return

                signal_measured = hp.get_data(start_time=0, end_time=-1).iloc[-nb_points_used:, :]
                output_data = hexapole.get_data(start_time=0, end_time=-1).values[-nb_points_used:, :]
                signal_wanted = signal_measured.copy()
                signal_wanted.iloc[:, :] = signal
                error = hp.calibration.data2inst(signal_measured - signal_wanted).values

                if np.max(np.abs(error)) < stop_criterion:
                    # print('Stopped tuning', '(Max tuning error: ', 27.26 * np.max(error), ' mT)')
                    break

                correction = np.zeros(error.shape)
                correction -= Kp * error
                # integral += error
                # correction += Ki * integral
                # derivative = error - previous_error
                # correction += Kd * derivative
                # previous_error = error.copy()
                output_data += correction
                output_data[:, :] = output_data.mean(0)
                current_signal = np.array([
                    lambda x: output_data[-1, 0] * np.ones(len(x)),
                    lambda x: output_data[-1, 1] * np.ones(len(x)),
                    lambda x: output_data[-1, 2] * np.ones(len(x))
                ])
                hexapole.stage_data(current_signal, 0.1, use_calibration=False, autostart=True, index_reset=True)
                # seems to be needed, do not make this too small
                time.sleep(0.1)

        print('Finishesd step experminet, zeroing magents')
        zero_magnet(moke)
        print('Zeroed the magnet')

    tuning_thread = threading.Thread(target=run_steps_experiment,
                                          args=[moke, signals, stop_event])
    tuning_thread.daemon = True
    tuning_thread.start()