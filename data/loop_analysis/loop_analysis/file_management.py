
import h5py
import numpy as np
import logging
import pandas as pd
import os
import git

try:
    GIT_SHA = git.Repo(search_parent_directories=True).head.object.hexsha
except ValueError:
    GIT_SHA = None


def get_file_data(file_name, group='/loops'):
    """Gets raw data from file"""
    with h5py.File(file_name, 'r') as file:
        loops = np.array(list(file.get(group).keys()))
        # get the loops period
        period = file.get(group).attrs['period']
        try:
            # skip the first loop if it was collected
            loop_nums = np.sort([int(l.split('data')[1])
                                 for l in loops if l != 'data1'])
        except IndexError:
            print('No loops found in the file')
            return
        # stack all the loops
        woll_list1 = []
        woll_list2 = []
        hp_list = []
        loop_num_list = []
        last_loop_num = 0

        for i, ln in enumerate(loop_nums):
            wl1 = np.array(file.get(group + '/data' +
                                    str(ln) + '/wollaston1/data')[:])
            woll_list1.append(wl1)

            wl2 = file.get(group + '/data' + str(ln) +
                           '/wollaston2/data')[:, 1:]
            woll_list2.append(wl2)

            hp = file.get(group + '/data' + str(ln) + '/hallprobe/data')[:, 1:]
            hp_list.append(hp)

            # use wollaston 1 as the timer for loops (should all be the same)
            wl1[:, 0] -= wl1[0, 0]
            loop_num_list.append(last_loop_num + 1 + wl1[:, 0] // period)
            # print(loop_num_list[-1])
            last_loop_num = loop_num_list[-1][-1]
            wl1[:, 0] %= period

    # stack the lists
    woll_full1 = np.vstack(woll_list1)
    woll_full2 = np.vstack(woll_list2)
    hp_full = np.vstack(hp_list)

    # combine the data
    data_full = np.hstack([woll_full1, woll_full2, hp_full, np.concatenate(
        loop_num_list)[:, None].astype(int)])
    data_fullpd = pd.DataFrame(data=data_full, columns=[
        "t", "woll1_det1", "woll1_det2", "woll2_det1", "woll2_det2", "Bx", "By", "Bz", "loop_number"])
    data_fullpd.astype({'loop_number': int})

    # get the moke signal
    data_fullpd['moke1'] = data_fullpd['woll1_det1'] / \
        data_fullpd['woll1_det2']
    data_fullpd['moke2'] = data_fullpd['woll2_det1'] / \
        data_fullpd['woll2_det2']

    return data_fullpd


def save_processed(save_file_path, data, peaks=None, group='', processing_parameters=None):
    """Saves the data to the file in save_file_path. Also saves the location of the peaks given as dict. 
    Optional is group path in which to save. processing_attrs is a dictionary containing the parameters used to get the peaks. """
    # check that the group doesn't already exist
    data_group_name = group + '/data'
    if os.path.exists(save_file_path):
        # if file exists, need to specify the group
        with h5py.File(save_file_path, 'r') as f:
            if data_group_name in f:
                logging.warning(
                    'The group already exists. Overwriting!')

    data.to_hdf(save_file_path, data_group_name, mode='a', format='fixed')

    if peaks is not None:
        peaks_grp_name = group + '/peaks'
        with h5py.File(save_file_path, 'a') as f:
            if peaks_grp_name not in f:
                peaks_grp = f.create_group(peaks_grp_name)
                for key in ['moke1', 'moke2']:
                    peaks_grp.create_dataset(key, data=peaks[key])
            else:
                for key in ['moke1', 'moke2']:
                    f[peaks_grp_name + '/' + key][:] = peaks[key]

    # save the processing parameters
    if processing_parameters is not None:
        processing_group = group + '/processing_params'
        with h5py.File(save_file_path, 'a') as f:
            if processing_group in f:
                del f[processing_group]
            grp = f.create_group(processing_group)
            for key, value in processing_parameters.items():
                grp[key] = value
            # save the git hash to know what version we are using
            if GIT_SHA is not None:
                grp.attrs['git sha'] = GIT_SHA
