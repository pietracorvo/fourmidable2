from time import sleep, time
import numpy as np

from experiments.basic import zero_magnet, deGauss
from experiments.take_loop import get_save_handle, append_save_instruments



# function that is run in a thread by take_steps
def take_steps(moke, signals, stop_event, saving_loc, data_callback, experiment_parameters):
    """
    Degauss and then use the pid to sequentially approach constant fields, trigger images
    of the camera and save them fo HDF.

    Args:
        moke: handle to moke object
        signals: Nx3 array of N field points for the 3 magnets that are sequentially approached by PID
        stop_event: Setting to True stops the loop
        saving_loc (None, str, group): file in which to save data. If None, a new file is created with default name. If str,
            A file is created at a given path. If group, the loops are saved in the given h5py group
        experiment_parameters: a dictionary with various parameters from the experiment parameter tree controlling
            details of the experiment
    """
    print_all_info = False   # NOTE for debugging steps experiment

    f = get_save_handle(saving_loc)
    grp = f.create_group('steps_experiment')
    info_grp = grp.create_group('info')
    inst_grp = grp.create_group('data')
    step_grp = inst_grp.create_group('steps')

    # Hardware specific info to save to HDF
    hp = moke.instruments['hallprobe']
    # TODO Ali implement fallback to HallProbe if senis not attached, currently it takes a not working senis if not attached
    senis = moke.instruments['bighall_fields']
    if experiment_parameters['measure_field_with_sensor'] == 'Senis':
        magnetic_field_sensor = senis
    else:
        magnetic_field_sensor = hp
    hexapole = moke.instruments['hexapole']
    camera_quanta = moke.instruments['quanta_camera']
    experiment_parameters['quantalux_exposure_time_ms'] = camera_quanta.exposure_time_ms
    experiment_parameters['quantalux_sensor_width_height'] = (camera_quanta.sensor_width_pixels, camera_quanta.sensor_height_pixels)
    experiment_parameters['quantalux_sensor_binningx_binningy'] = camera_quanta.binning
    experiment_parameters['quantalux_hotpixelcorrection_isactive'] = camera_quanta.is_hotpixelcorrection_active
    if experiment_parameters['quantalux_hotpixelcorrection_isactive']:
        experiment_parameters['quantalux_hotpixelcorrection_threshold'] = camera_quanta.get_hotpixelcorrection_threshold

    # Experiment specific parameters
    apply_pid_iteratively = False
    take_reference_image = experiment_parameters['take_reference_image']
    degauss = experiment_parameters['degauss']
    nb_loops = experiment_parameters['nb_loops']
    skip_loops = experiment_parameters['skip_loops']
    nb_images_per_step = experiment_parameters['nb_images_per_step']
    only_save_average_of_images = experiment_parameters['only_save_average_of_images']
    Kp = experiment_parameters['Kp']
    # Ki = 0.5   # for I in PID, seems not to work
    # Kd = 0.5   # for D in PID, seems not to work
    nb_points_used_for_tuning = experiment_parameters['nb_points_used_for_tuning']   # 1 point should equal 0.0001s
    stop_criterion_tuning = experiment_parameters['stop_criterion_tuning_mT']  # noise less than X mT
    for k, v in experiment_parameters.items():
        #print(k,v)
        info_grp.attrs[k] = v

    if degauss:
        deGauss(moke)

    # If desired, take a reference image before any field applied
    if take_reference_image:
        image_data = []
        for j in range(nb_images_per_step):
            image_data.append(camera_quanta.get_single_image().copy())
            if print_all_info: print(f'    --> Shooting reference image number {j} before applying fields')
        image_data = np.stack(image_data, axis=2)
        if only_save_average_of_images:
            image_data = np.mean(image_data, axis=2)
        info_grp.create_dataset('reference_image_no_field', data=image_data)

    start_time = hexapole.get_data(start_time=0, end_time=-1).index[-1]
    last_signal_end_time = start_time
    sleep(0.1)

    # This array collects the results of the PID from previous loop to use it in next loop
    last_pid_results = [None] * signals.shape[0]

    idx_loop = 0
    idx_step = 0
    while idx_loop < nb_loops or nb_loops == -1:

        for i, signal in enumerate(signals):
            # previous_error = np.zeros((nb_points_used_for_tuning, 3))   # NOTE for not used ID parts in PID
            # integral = np.zeros((nb_points_used_for_tuning, 3))

            counter_while_loop = -1
            while True:
                counter_while_loop += 1
                if print_all_info: print(f'LOOP TUNING  ---->  loop={idx_loop}', f'step={i} trials_adjust_field_loop={counter_while_loop}')

                # if stop event is set stop the experiment
                if stop_event.is_set():
                    zero_magnet(moke)
                    return

                # If voltage guesses already present from last PID iteration, try them on
                # hexapole first (BUT only once!), before running the PID from guesses
                if apply_pid_iteratively and last_pid_results[i] is not None and counter_while_loop == 0:
                    if print_all_info: print('    --> Try last loops PID result ')
                    guess_signal = np.array([
                        lambda x: last_pid_results[i][0] * np.ones(len(x)),
                        lambda x: last_pid_results[i][1] * np.ones(len(x)),
                        lambda x: last_pid_results[i][2] * np.ones(len(x))
                    ])
                    hexapole.stage_data(guess_signal, 0.1, use_calibration=False,
                                        autostart=True, index_reset=True)
                    if print_all_info: print('    --> last loops PID result sent to hexapole')
                    sleep(0.0001)   # NOTE maybe not needed
                    last_signal_end_time = hexapole.get_data(start_time=last_signal_end_time, end_time=-1).index[-1]
                    sleep(0.0001)   # NOTE maybe not needed

                # Just get the last nb_points_used_for_tuning of hexapole & hp for PID
                if print_all_info: print('    --> trying to get last output_data from hexapole')
                signal_measured = magnetic_field_sensor.get_data(start_time=last_signal_end_time,
                                              end_time=-1).iloc[-nb_points_used_for_tuning:, :]
                output_data = hexapole.get_data(start_time=last_signal_end_time,
                                                end_time=-1).iloc[-nb_points_used_for_tuning:, :]
                if len(signal_measured) < 1 or len(output_data) != len(signal_measured):
                    sleep(0.0001)
                    continue
                signal_wanted = signal_measured.copy()
                signal_wanted.iloc[:, :] = signal  # put constant signal at all times
                if print_all_info: print('    --> got last output_data from hexapole')

                # Stop tuning for targeted signal if current signal is good enough, take images and save them
                error_in_millitesla = (signal_measured - signal_wanted).values
                if print_all_info: print(f'    --> NEW ERROR: mean={round(np.mean(np.abs(error_in_millitesla)),4)} std={round(np.std(np.abs(error_in_millitesla)),4)} max={round(np.max(np.abs(error_in_millitesla)),4)}')
                if np.mean(np.abs(error_in_millitesla)) < stop_criterion_tuning:
                    last_pid_results[i] = output_data.iloc[-1,:].values
                    if print_all_info: print('    --> updated last_pid_results\n\t\t', last_pid_results)

                    # If skip current loop, record NO data
                    if idx_loop < skip_loops:
                        break

                    # Take nb images for averaging
                    image_data = []
                    for j in range(nb_images_per_step):
                        image_data.append(camera_quanta.get_single_image().copy())
                        if print_all_info: print(f'    --> take picture number {j}')
                    if print_all_info: print('    --> all pictures taken')
                    image_data = np.stack(image_data, axis=2)  # stack images along 3rd coordinate (like h5 format does)

                    # Save all the stuff to HDF
                    current_signal_stabilized_time = output_data.index[-1]
                    time_all_images_were_taken = hexapole.get_data(start_time=-3, end_time=-1).index[-1]
                    append_save_instruments(moke, inst_grp, ['hexapole', 'hallprobe', 'bighall_fields'],
                                     start_time=last_signal_end_time, end_time=current_signal_stabilized_time)
                    nth_step_grp = step_grp.create_group(str(idx_step))
                    nth_step_grp.attrs['time_signal_stability_reached'] = current_signal_stabilized_time
                    nth_step_grp.attrs['target_signal'] = signal
                    nth_step_grp.attrs['hp_measured_signal'] = signal_measured.iloc[-1, :].values
                    nth_step_grp.attrs['time_all_images_were_taken'] = time_all_images_were_taken
                    # TODO maybe also add Senis field if availale
                    if only_save_average_of_images:
                        image_data = np.mean(image_data, axis=2)
                    nth_step_grp.create_dataset('image_data', data=image_data)
                    data_callback(current_signal_stabilized_time, signal_measured.iloc[-1, :].values, image_data)
                    time_all_data_saved_to_hdf = hexapole.get_data(start_time=-3, end_time=-1).index[-1]
                    nth_step_grp.attrs['time_all_data_saved_to_hdf'] = time_all_data_saved_to_hdf
                    last_signal_end_time = current_signal_stabilized_time
                    if print_all_info: print('    --> data written to HDF')
                    break

                # If signal stability not reached, try a new PID step
                if print_all_info: print('    --> run PID: take difference signal_measured - signal_wanted and correct')
                error_in_volts = hp.calibration.data2inst(signal_measured - signal_wanted).values
                correction = np.zeros(error_in_volts.shape)
                correction -= Kp * error_in_volts
                # integral += error                # NOTE for not used ID parts in PID
                # correction += Ki * integral
                # derivative = error - previous_error
                # correction += Kd * derivative
                # previous_error = error.copy()

                # Make an array of constant functions with new voltages to send to hexapole
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
                if print_all_info: print('    --> new PID corrected signal sent to hexapole')
            idx_step += 1
        idx_loop += 1

    zero_magnet(moke)
    print('Finished step experiment, zeroing magnets')
    f.file.close()
