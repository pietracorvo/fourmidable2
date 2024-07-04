from time import sleep
import threading
import numpy as np

from experiments.basic import zero_magnet, deGauss
from experiments.take_loop import get_save_handle, append_save_instruments


def take_steps(moke, signals, stop_event, saving_loc, experiment_parameters):
    """
    Degauss and then use the pid to sequentially apply constant fields.

    Args:
        moke: handle to moke object
        signals: Nx3 array of N field points for the 3 magnets that are sequentially approached by PID
        stop_event: Setting to True stops the loop
    """
    tuning_thread = threading.Thread(target=run_steps_experiment,
                                     args=[moke, signals, stop_event, saving_loc, experiment_parameters])
    tuning_thread.daemon = True
    tuning_thread.start()


# function that is run in a thread by take_steps
def run_steps_experiment(moke, signals, stop_event, saving_loc, experiment_parameters):

    f = get_save_handle(saving_loc)
    grp = f.create_group('steps_experiment')
    info_grp = grp.create_group('info')
    inst_grp = grp.create_group('data')
    step_grp = inst_grp.create_group('steps')

    hp = moke.instruments['hallprobe']
    hexapole = moke.instruments['hexapole']
    camera_quanta = moke.instruments['quanta_camera']

    nb_images_per_step = experiment_parameters['nb_images_per_step']
    only_save_average_of_images = experiment_parameters['only_save_average_of_images']
    Kp = experiment_parameters['Kp']
    # Ki = 0.5   # for I in PID, seems not to work
    # Kd = 0.5   # for D in PID, seems not to work
    nb_points_used_for_tuning = experiment_parameters['nb_points_used_for_tuning']   # 1 point should equal 0.0001s
    stop_criterion_tuning = experiment_parameters['stop_criterion_tuning_mT']  # noise less than X mT
    for k, v in experiment_parameters.items():
        info_grp.attrs[k] = v

    deGauss(moke)

    start_time = hexapole.get_data(start_time=0, end_time=-1).index[-1]
    last_signal_end_time = start_time
    sleep(0.1)
    for i, signal in enumerate(signals):
        # previous_error = np.zeros((nb_points_used_for_tuning, 3))
        # integral = np.zeros((nb_points_used_for_tuning, 3))

        while True:
            if stop_event.is_set():
                zero_magnet(moke)
                return

            # Just get the last nb_points_used_for_tuning of hexapole & hp for PID
            signal_measured = hp.get_data(start_time=last_signal_end_time,
                                          end_time=-1).iloc[-nb_points_used_for_tuning:, :]
            output_data = hexapole.get_data(start_time=last_signal_end_time,
                                            end_time=-1).iloc[-nb_points_used_for_tuning:, :]
            if len(signal_measured) < 1 or len(output_data) != len(signal_measured):
                sleep(0.0001)
                continue
            signal_wanted = signal_measured.copy()
            signal_wanted.iloc[:, :] = signal  # put constant signal at all times
            error = hp.calibration.data2inst(signal_measured - signal_wanted).values

            # Stop tuning for targeted signal if current signal is good enough, take images and save them
            error_in_millitesla = (signal_measured - signal_wanted).values
            if np.mean(np.abs(error_in_millitesla)) < stop_criterion_tuning:
                image_data = []
                for j in range(nb_images_per_step):
                    image_data.append(camera_quanta.get_data().copy())
                    #print(i,j)   # TODO remove
                image_data = np.stack(image_data, axis=2)   # stack images along 3rd coordinate
                current_signal_end_time = output_data.index[-1]
                append_save_instruments(moke, inst_grp, ['hexapole', 'hallprobe'],
                                 start_time=last_signal_end_time, end_time=current_signal_end_time)
                nth_step_grp = step_grp.create_group(str(i))
                nth_step_grp.attrs['time_signal_stability_reached'] = current_signal_end_time
                nth_step_grp.attrs['target_signal'] = signal
                nth_step_grp.attrs['hp_measured_signal'] = signal_measured.iloc[-1, :].values
                if only_save_average_of_images:
                    image_data = np.mean(image_data, axis=2)
                nth_step_grp.create_dataset('image_data', data=image_data)
                last_signal_end_time = current_signal_end_time
                break

            correction = np.zeros(error.shape)
            correction -= Kp * error
            # integral += error
            # correction += Ki * integral
            # derivative = error - previous_error
            # correction += Kd * derivative
            # previous_error = error.copy()

            output_data = output_data.values
            output_data += correction
            output_data[:, :] = output_data.mean(0)   # apply mean instead of error from noisy hallprobes
            current_signal = np.array([
                lambda x: output_data[-1, 0] * np.ones(len(x)),
                lambda x: output_data[-1, 1] * np.ones(len(x)),
                lambda x: output_data[-1, 2] * np.ones(len(x))
            ])
            hexapole.stage_data(current_signal, 0.1, use_calibration=False,
                                autostart=True, index_reset=True)

    zero_magnet(moke)
    print('Finished step experiment, zeroing magnets')
    f.file.close()
