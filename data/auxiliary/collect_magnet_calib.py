import pandas as pd
import numpy as np
import h5py
import os
from tqdm import tqdm

def collect_fft_data(folder, out_file, freq_resolution=0.1, cutoff_freq=100):
    file = h5py.File(os.path.join(out_file))
    out_keys = np.array(list(file.keys())).astype(str)
    # get the data labels and find the maximum one
    if len(out_keys) == 0:
        next_store_num = 1
    else:
        next_store_arr = [0]*len(out_keys)
        for i, k in enumerate(out_keys):
            next_store_arr[i] = int(k.split('data')[1])
        next_store_num = np.max(next_store_arr)+1
    file.close()

    # create the indices for saving df
    tuples = [('hexapole', 'A', 'amplitude'), ('hexapole', 'A', 'phase'),
              ('hexapole', 'B', 'amplitude'), ('hexapole', 'B', 'phase'),
              ('hexapole', 'C', 'amplitude'), ('hexapole', 'C', 'phase'),
              ('hallprobe', 'A', 'amplitude'), ('hallprobe', 'A', 'phase'),
              ('hallprobe', 'B', 'amplitude'), ('hallprobe', 'B', 'phase'),
              ('hallprobe', 'C', 'amplitude'), ('hallprobe', 'C', 'phase')
              ]
    multiindx = pd.MultiIndex.from_tuples(tuples)
    inst_list = ['hexapole', 'hallprobe']

    # go through all the files in the given folder and get their data
    file_list = os.listdir(folder)
    for fi, file_name in enumerate(file_list):
        print('\nFile ', fi + 1, '/', len(file_list))
        # get the list of data points
        file = h5py.File(os.path.join(folder, file_name))
        data_points = list(file.keys())
        # only take the ones for which there are both datasets
        data_points_to_remove = []
        for dp in data_points:
            grp = file[dp]
            for inst in inst_list:
                if inst not in grp.keys():
                    data_points_to_remove.append(dp)
                    print('Data point ', dp, ' not complete')
                    break
        for dp in data_points:
            if dp in data_points_to_remove:
                data_points.remove(dp)
        file.close()

        # go through the data points and for each do the fft and store the data
        for dp in tqdm(data_points):
            fft_data = pd.DataFrame(np.zeros((int(cutoff_freq / freq_resolution), len(tuples))))
            fft_data['freq'] = (np.arange(0, cutoff_freq, freq_resolution)*10).astype(int)
            fft_data.set_index('freq', inplace=True)
            fft_data.columns = multiindx
            for inst in inst_list:
                # get the data and do fft
                file = h5py.File(os.path.join(folder, file_name))
                if inst in file[dp].keys():
                    inst_data = pd.DataFrame(np.array(file.get(dp + '/' + inst + '/data/table'))).set_index('index')
                else:
                    print('No dataset ' + dp + '/' + inst + '/data')
                    break
                file.close()
                inst_fft = np.fft.rfft(inst_data, axis=0)
                freq = np.fft.rfftfreq(inst_data.shape[0], inst_data.index[1] - inst_data.index[0])
                # filter fft for the required frequencies

                # bin the data
                bins = np.arange(0, cutoff_freq, freq_resolution)
                for i, pole in enumerate(['A', 'B', 'C']):
                    signal_fft = pd.DataFrame()
                    signal_fft.loc[:, 'freq'] = freq
                    signal_fft.loc[:, 'fft_real'] = np.real(inst_fft[:, i])
                    signal_fft.loc[:, 'fft_imag'] = np.imag(inst_fft[:, i])
                    signal_fft.loc[:, 'bins'] = pd.cut(signal_fft['freq'], bins=bins, right=False)
                    signal_fft_means = signal_fft.groupby('bins').sum().reset_index()
                    signal_fft_means.dropna(inplace=True)
                    signal_fft_means['amplitude'] = np.abs(
                        signal_fft_means['fft_real'] + 1j * signal_fft_means['fft_imag'])
                    signal_fft_means['phase'] = np.angle(
                        signal_fft_means['fft_real'] + 1j * signal_fft_means['fft_imag'])
                    signal_fft_means.loc[:, 'freq'] = signal_fft_means.loc[:, 'bins'].apply(lambda x:int(x.left*10))
                    signal_fft_means.set_index('freq', inplace=True)
                    fft_data.loc[signal_fft_means.index, (inst, pole, 'amplitude')] = signal_fft_means.loc[:, 'amplitude']
                    fft_data.loc[signal_fft_means.index, (inst, pole, 'phase')] = signal_fft_means.loc[:, 'phase']
            # save the acquired fft_data
            out_store = pd.HDFStore(out_file)
            # make frequencies floats again
            fft_data.index /= 10
            out_store.put('/data' + str(next_store_num), fft_data, format='table')
            next_store_num += 1
            out_store.close()


def extract_nn_training_data(file_name):
    # get the data keys
    with h5py.File(file_name) as file:
        data_keys = list(file.keys())
        # get the length of one of the data sets
        data_length = file[data_keys[0]]['table'].shape[0]
    # create numpy arrays
    magcalib_data_hp = np.zeros((len(data_keys), data_length, 6))
    magcalib_data_hx = np.zeros((len(data_keys), data_length, 6))
    # iterate through the datasets and get the values
    with pd.HDFStore(file_name) as store:
        for i, dk in enumerate(tqdm(data_keys)):
            data_table = store[dk]
            magcalib_data_hp[i, :, :] = np.array(data_table['hallprobe'])
            magcalib_data_hx[i, :, :] = np.array(data_table['hexapole'])
    # save the data
    np.save('hp_training.npy', magcalib_data_hp[:-300, :, :])
    np.save('hx_training.npy', magcalib_data_hx[:-300, :, :])
    np.save('hp_testing.npy', magcalib_data_hp[-300:, :, :])
    np.save('hx_testing.npy', magcalib_data_hx[-300:, :, :])


if __name__ == '__main__':
    folder = '/media/luka/ls604_data/MagCalib'
    out_file = 'MagCalib_fft.h5'
    collect_fft_data(folder, out_file)
    extract_nn_training_data(out_file)
