import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


def wollaston_data(data):
    """Gets the data for wollaston lens from basic data.

        Args:
            data (numpy array): numpy array with 2 rows (s and p data respectively)

        Returns:
            average
    """
    data = data.assign(average=(data.loc[:, "det1"] + data.loc[:, "det2"]) / 2,
                       difference=(data.loc[:, "det1"] - data.loc[:, "det2"]) / 2)
    return data


def prepare_for_plotting(data, n_points, smooth_window=10):
    """Prepares NI data for plotting by undersampling and smoothing"""
    if n_points == 0:
        return pd.DataFrame(columns=data.columns)
    n_data = data.shape[0]
    if n_data != 0:
        step = int(np.ceil(n_data / n_points))
    else:
        return data
    undersampled_data = data.rolling(
        smooth_window, min_periods=1, center=False).mean().iloc[(n_data - 1) % step::step]
    return undersampled_data


# this function is for live data processing from the take_loop experiment data_callback.
def get_binned_data(inst_data, n_periods=1, data_per_period=200):
    """Gets the binned data ready for live plotting based on the inst_data dictionary which should contain both
    wollastons and hp data"""
    hp_data = inst_data['hallprobe'].reset_index()
    woll_data1 = inst_data['wollaston1'].reset_index()
    woll_data2 = inst_data['wollaston2'].reset_index()
    woll_data1.drop(columns=['t'], inplace=True)
    woll_data1.rename(
        columns={'det1': 'woll1det1', 'det2': 'woll1det2'}, inplace=True)
    woll_data2.drop(columns=['t'], inplace=True)
    woll_data2.rename(
        columns={'det1': 'woll2det1', 'det2': 'woll2det2'}, inplace=True)
    # concat the data into one dataframe
    data_full = pd.concat(
        [hp_data, woll_data1, woll_data2], axis=1, sort=False)

    # set the timing of each period such that it starts at 0
    # there should be an integer number of periods samples in data
    samples_per_period = int(np.floor(data_full.shape[0] / n_periods))
    for i in range(n_periods - 1):
        data_full.loc[samples_per_period * i:samples_per_period
                      * (i + 1) - 1, "t"] -= data_full.loc[samples_per_period * i, "t"]
    # this is just not to get messed up by one extra data point which can sometimes happen
    i = n_periods - 1
    data_full.loc[samples_per_period * i:,
                  "t"] -= data_full.loc[samples_per_period * i, "t"]

    t = np.array(data_full.loc[:, "t"])
    bins = np.linspace(np.min(t), np.max(t), data_per_period)
    data_full['bins'] = pd.cut(t, bins=bins, right=False)

    # bin in time and stack
    data_binned = data_full.groupby('bins').mean().reset_index()
    data_binned.reset_index(inplace=True)
    data_binned.drop(columns=['bins'], inplace=True)

    # get the sum, difference and the ratio for the both wollastons
    data_binned['diff1'] = (data_binned['woll1det1']
                            - data_binned['woll1det2']) / 2
    data_binned['sum1'] = (data_binned['woll1det1']
                           + data_binned['woll1det2']) / 2
    data_binned['ratio1'] = data_binned['woll1det1'] / data_binned['woll1det2']

    data_binned['diff2'] = (data_binned['woll2det1']
                            - data_binned['woll2det2']) / 2
    data_binned['sum2'] = (data_binned['woll2det1']
                           + data_binned['woll2det2']) / 2
    data_binned['ratio2'] = data_binned['woll2det1'] / data_binned['woll2det2']
    return data_binned
