from experiments.basic import deGauss, temp_too_high, zero_magnet
from data.signal_generation import get_const_signal, get_zeros_signal
import traceback
import pandas as pd
import h5py
import numpy as np
import time


def field_map_unidirectional(moke, movement_range=[-1000, 1000], direction='x', step=100,
                             recording_interval=0.1, stop_event=None, data_callback=None,
                             magnet_signal=[1, 1, 1], save_data=False):
    """Moves the stage in the given movement_range across the direction x and records field values at given intervals

    Args:
        moke: handle to moke object
        movement_range: size of the scan
        direction: direction of the scan
        step: step between the positions
        recording_interval: how long are we recording for
        stop_event: threading event which gets checked for experiment stopping
        data_callback: every interval the acquired data is sent to the callback function (e.g. for plotting)
        magnet_signal: the signal magnet is outputting throughout the experiment
        save_data: should the program save to a file flag
    """
    try:
        # use only the linear stage part
        stage = moke.instruments['stage']
        magnet = moke.instruments['hexapole']
        bighall = moke.instruments['bighall_fields']

        # get the index of the position
        indx = stage.direction_labels.index(direction)

        if movement_range[0] > movement_range[1]:
            step = -step
        positions = np.arange(
            movement_range[0] - step, movement_range[1] + step, step)

        # go to the starting position
        print('Moving to the starting position...')
        stage.set_position({direction: positions[0]},
                           relative=True, wait=True)
        # degauss and start applying the fields
        deGauss(moke)
        magnet.stage_data(get_const_signal(magnet_signal), 1,
                          autostart=True, use_calibration=False)
        # give the magnet 5 seconds for the fields to stabilise
        time.sleep(5)

        # once the starting position is reached, start moving
        # in the desired direction and record the position and fields every given time interval
        print('Recording fields...')
        full_data = pd.DataFrame(columns=["position", "field"])
        for pos in positions:
            if stop_event.is_set():
                break
            stage.set_position({direction: step}, relative=True, wait=True)
            # if the temperature is too high, abort the experiment
            if temp_too_high(moke, print_values=False):
                break

            # get the position and field data
            position = stage.get_position()[indx]
            start_time = bighall.get_time()
            end_time = start_time + recording_interval
            # get the norm of the mean of the fields in the interval
            field = np.linalg.norm(bighall.get_data(start_time=start_time,
                                                    end_time=end_time, wait=True).mean())

            # append to full data of the experiment
            full_data = full_data.append(pd.DataFrame(
                np.array([[position, field]]), columns=["position", "field"]), ignore_index=True)
            if data_callback is not None:
                data_callback(position, field)

        print('Experiment done, stopping...')
        # stop the experiment
        zero_magnet(moke)
        stage.stop()

        if save_data:
            print('Saving data...')
            # create a file to save the experiment in
            filename = 'FieldMapping' + direction + \
                time.strftime("%Y%m%d-%H%M%S") + '.h5'
            print('Saving to ', filename)

            with h5py.File(filename, 'w') as f:
                f.create_group('data')
                f.attrs['direction'] = direction.encode('utf8')
            with pd.HDFStore(filename) as store:
                store.put('data', full_data, data_columns=True, format='table')
        print('Done!')

    except:
        traceback.print_exc()
