#from data.slack_message import send_slack
from ..take_loop import take_sin_loop
import numpy as np
from auxiliary.file_manipulations import create_safe_filename, append_datetimestr
from experiments.basic import switch_laser, temp_too_high_stop
import time
import h5py
import os
from copy import copy


def test12_(*args, **kwargs):
    print('hello    ')


def amp_sweep_(moke, stop_event=None, loop_widget=None, file_name=None, folder=None):
    """Custom experiment that is run by the loop widget.
    Note: the name has to finish with _ to be used in the list of functions in the loop widget"""
    # define the parameters
    skip_loops = 10
    n_loops = 10
    period = 1.1
    start_amp = 2
    stop_amp = 46
    step_amp = 2

    steps = int((1 + (stop_amp - start_amp) / step_amp))
    # prepare the angles and offsets
    amps = np.linspace(start_amp, stop_amp, steps)
    print(amps)

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
        file_name = append_datetimestr('Amp_sweep.h5')
    if folder is not None:
        file_name = os.path.join(folder, file_name)

    # create the saving location
    #send_slack('Starting loop map')

        # do the sweep
        for i in range(steps):

            if stop_event.is_set():
                break
            print('Running {} map'.format(i))
            direction_file_name = os.path.splitext(
                file_name)[0] + '_' + str(i) + os.path.splitext(file_name)[1]
            direction_file_name = create_safe_filename(
                direction_file_name, ext='.h5')
            print('Saving to: ', direction_file_name)
            with h5py.File(direction_file_name, 'w') as f:
                 # create a group
                grp = f.create_group('Amp sweep')
                # add some attributes to the group
                grp.attrs['Date taken'] = time.strftime("%Y%m%d-%H%M%S")
                grp.attrs['Field amp'] = str(i)
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
                    amp = amps[i]
                    gname = format('Amp_' + str(amp))
                    print (gname)
                    saving_group = grp.create_group(gname)
                    # Here we select the field axis
                    amplitudes = amp * np.array([1, 0, 0.306])
                    print('Doing amplitude ', amp)

                else:
                    raise Exception('One of the directions not recognised!')

                saving_group.attrs['Field amp'] = str(amp)

                # take the loop with these parameters
                take_sin_loop(moke,
                            amplitudes=amplitudes, frequency=1 / period,
                            stop_event=stop_event, data_callback=update_plot_data,
                            skip_loops=skip_loops, n_loops=n_loops, tune_loop=True, saving_loc=saving_group)

    #send_slack('Loop map done!')
    # turn the laser off if did not stop manually
    if not stop_event.is_set():
        switch_laser(moke, False)
