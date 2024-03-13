#from data.slack_message import send_slack
from ..take_loop import take_sin_loop
import numpy as np
from ..find_maximum import find_maximum
from auxiliary.file_manipulations import create_safe_filename, append_datetimestr
from experiments.basic import switch_laser, temp_too_high_stop
import time
import h5py
import os
from copy import copy


def senis_map_(moke, stop_event=None, loop_widget=None, file_name=None, folder=None):
    """Custom experiment that is run by the loop widget.
    Note: the name has to finish with _ to be used in the list of functions in the loop widget"""
    # define the parameters
    skip_loops = 10
    n_loops = 20
    field_amp = 20
    period = 1.1
    n_angles = 3  # how many angles between 0 and pi
    start_angle = 0
    stop_angle = np.pi
    find_max_startstep = 0.5
    find_max_endstep = 0.2
    angle = 0

    # prepare the angles and offsets
    angles = np.linspace(start_angle, stop_angle, n_angles)
    print(angles)

    # make sure you have the correct loop tuning parameters
    update_plot_data = None

    # expect this to be run by the loop widget
    if loop_widget is not None:
        file_name = copy(loop_widget.params.child(
            'Running Custom Experiment', 'File name').value())
        folder = copy(loop_widget.saving_dir)
        stop_event = loop_widget.stop_event
        # clear the data for display
        loop_widget.clear_data()
        # define the data callback
        update_plot_data = loop_widget.update_plot_data

    if file_name is None or file_name == '':
        file_name = append_datetimestr('Senis_Data.h5')
    if folder is not None:
        file_name = os.path.join(folder, file_name)

    # create the saving location
    #send_slack('Starting loop map')
    # Possible options: 'xz_offset_struct', 'xz_offset', 'xz', 'xy'
    for directions in ['xz_offset_struct', 'xz_offset']:  # 'xz', 'xy',
        if stop_event.is_set():
            break
        print('Running {} map'.format(directions))
        direction_file_name = os.path.splitext(
            file_name)[0] + '_' + directions + os.path.splitext(file_name)[1]
        direction_file_name = create_safe_filename(
            direction_file_name, ext='.h5')
        print('Saving to: ', direction_file_name)
        with h5py.File(direction_file_name, 'w') as f:
            # create a group
            grp = f.create_group('Loop Map')

            # add some attributes to the group
            grp.attrs['Date taken'] = time.strftime("%Y%m%d-%H%M%S")
            grp.attrs['Field amp'] = field_amp
            grp.attrs['Field period'] = period

            # make sure the magnets are not overheating
            temp_too_high_stop(moke, stop_event=stop_event)
            # stop the loop if event set
            if stop_event.is_set():
                break

            if loop_widget is not None:
                # clear the data for display
                loop_widget.clear_data()
                # get the field amplitudes
                # do the xy sweep
                saving_group = grp.create_group('SenisTest_')
                amplitudes = field_amp * np.array([np.cos(angle), np.sin(angle), 0])


            else:
                raise Exception('One of the directions not recognised!')

            saving_group.attrs['angle'] = np.rad2deg(angle)

            # find the maximum of the signal
            find_maximum(moke, start_step=find_max_startstep,
                            end_step=find_max_endstep, stop_event=stop_event)
            if stop_event.is_set():
                break
            # take the loop with these parameters
            take_sin_loop(moke,
                            amplitudes=amplitudes, frequency=1 / period,
                            stop_event=stop_event, data_callback=update_plot_data,
                            skip_loops=skip_loops, n_loops=n_loops, tune_loop=True, saving_loc=saving_group, saving_instruments='bighall_fields')

    #send_slack('Loop map done!')
    # turn the laser off if did not stop manually
    if not stop_event.is_set():
        switch_laser(moke, False)
