import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.fftpack import next_fast_len
from .tvregdiff.tvregdiff import TVRegDiff
from scipy.signal import find_peaks


def get_averaged_loop(raw_data, data_per_period=1000):
    t = raw_data['t']
    mnt = np.min(t)
    mxt = np.max(t)
    bins = np.linspace(mnt, mxt, data_per_period + 1)
    raw_data['bins'] = pd.cut(t, bins=bins, right=False)

    # bin in time and stack
    data_binned = raw_data.groupby('bins').mean().reset_index()
    data_binned.dropna(inplace=True)
    data_binned.drop(columns='loop_number', inplace=True)

    return data_binned


def get_fields_dir_vector(data):
    """Gets the direction of applied fields"""
    fields = data.loc[:, ['Bx', 'By', 'Bz']].copy()
    # remove offsets
    fields -= np.mean(fields)
    # get the field magnitude
    norm_field = np.linalg.norm(fields, axis=1)
    # get the direction along which field is applied
    idx = np.argmax(norm_field)
    dir_vector = np.array(fields.iloc[idx]) / norm_field[idx]
    # make the direction vector point towards positive x for consistency
    dir_vector *= np.sign(dir_vector[0])
    return dir_vector


def get_fields_angle(data):
    a, _ = np.polyfit(data['Bx'], data['Bz'], 1)
    angle = np.rad2deg(np.arctan(a))
    return angle


def get_kerr_signal(data, plot=False, cutoff=0.2, stage_angle=15):
    """Adjust for the Faraday rotation by flattening moke loops.
    Note: this assumes that the field is oscillating along one direction and is not e.g. circular
    Args:
        data (pandas): moke data
        plot (bool): weather or not to plot the steps to see if the procedure is working well
        cutoff (float): (1-cutoff)*max_fields is the field at which the sample is assumed to be saturated
        stage_angle (float): angle of the stages in degrees for calculating the direction of the fields relevant for the Faraday effect correction.
    """
    fields = data.loc[:, ['Bx', 'By', 'Bz']].values

    # get the fields in the table FOR
    stage_angle = np.deg2rad(stage_angle)
    c, s = np.cos(stage_angle), np.sin(stage_angle)
    rotmat = np.array(((c, 0, s), (0, 1, 0), (-s, 0, c)))
    fields_table = fields.dot(rotmat.T)
    lens_fields = fields_table[:, 0]

    # get the direction along which field is applied
    direction = get_fields_dir_vector(data)
    fields_dir = fields.dot(direction)
    # get the indx selecting large positive and negative fields separately
    large_fields_idx = dict()
    for sgn in [-1, 1]:
        fields_sgn = sgn * fields_dir
        max_field = np.max(np.abs(fields_dir[fields_sgn > 0]))
        large_fields_idx[sgn] = fields_sgn > (1 - cutoff) * max_field

    if plot:
        fig, ax = plt.subplots(2, 2, figsize=(10, 8))
        ax[0, 0].set_ylabel('Before')
        ax[1, 0].set_ylabel('After')
    # do it for both the
    for i, (key, moke) in enumerate(data.filter(regex='moke*').items()):
        if plot:
            ax[0, i].plot(lens_fields, moke)
            ax[0, i].set_title('Detector ' + str(i))
        # faraday coefficient and the average of the saturated regions.
        # acquried as the average of positive and negative high fields
        k = 0
        avg = 0
        # take the top of the fields in negative and in positive separately
        for sgn in [-1, 1]:
            idx = large_fields_idx[sgn]
            # if not np.any(idx):
            #     k *= 2
            #     continue
            x, y = lens_fields[idx], moke[idx].values
            # sort for the fit
            sortidx = np.argsort(x)
            xsorted, ysorted = x[sortidx], y[sortidx]
            # fit a line to data
            a, b = np.polyfit(xsorted, ysorted, 1)
            k += a / 2
            if plot:
                ax[0, i].plot(lens_fields[idx], y)
                ax[0, i].plot(lens_fields, a * lens_fields + b)
        data[key] -= k * lens_fields
        # get the average of large fields data
        avg = np.mean([np.mean(data[key][large_fields_idx[sgn]])
                       for sgn in [-1, 1]])  # if np.any(large_fields_idx[sgn])])
        # normalise the signal to get the imaginary part of moke kerr (see theory)
        data[key] = 1 / 4 * (1 - data[key] / avg)

        if plot:
            ax[1, i].plot(fields_dir, data[key])
    return data


def fft_shift(data, period_fraction=None):
    """Shifts the data (except t column) by the fraction of the period. 

    If the period fraction is None, try guessing the shift from the fields. This will shift in a way that will make the fields fourier transfrorm of the base frequency have 0 phase. I.e. this will result in the fields being cosines in the base frequency. Note: This only works if the fields are in phase at the base frequency!"""
    # bins are not numbers, so can't shift that
    data_shifted = data.drop(columns=['bins'])
    # select everything except the first column which should be time
    all_vals = data_shifted.to_numpy()[:, 1:]
    # do fft and add phase shift
    fft = np.fft.rfft(all_vals, n=all_vals.shape[0], axis=0)
    freq = np.fft.rfftfreq(all_vals.shape[0])
    if period_fraction is None:
        # fields are at indices 4, 5, 6
        time_shift = -np.angle(np.sum(fft[1, 4:7])) / (2 * np.pi * freq[1])
    else:
        time_shift = all_vals.shape[0] * period_fraction

    fft *= np.exp(1j * 2 * np.pi * freq * time_shift)[:, np.newaxis]
    # calculate the inverse fft
    all_vals_shifted = np.fft.irfft(fft, n=all_vals.shape[0], axis=0)
    data_shifted.values[:, 1:] = all_vals_shifted
    return data_shifted


def fft_shift_fields(data):
    """Shifts the data (except t column) in a way that will make the fields fourier transfrorm of the base frequency have 0 phase. I.e. this will result in the fields being cosines in the base frequency. Note: This only works if the fields are in phase at the base frequency!"""
    # bins are not numbers, so can't shift that
    data_shifted = data.drop(columns=['bins'])
    # select everything except the first column which should be time
    all_vals = data_shifted.to_numpy()[:, 1:]
    fft = np.fft.rfft(all_vals, n=all_vals.shape[0], axis=0)
    freq = np.fft.rfftfreq(all_vals.shape[0])
    period = all_vals.shape[0]
    # assume that the fields are period with this period
    time_shift = -np.angle(np.sum(fft[1, 4:7])) / (2 * np.pi * freq[1])
    print(time_shift)
    fft *= np.exp(1j * 2 * np.pi * freq * time_shift)[:, np.newaxis]
    all_vals_shifted = np.fft.irfft(fft, n=all_vals.shape[0], axis=0)
    data_shifted.values[:, 1:] = all_vals_shifted
    return data_shifted


def get_derivative(data, diff_reg=1e-6, peak_height=5e-3, peak_prominence=1e-3):
    """Gets the derivative of the moke signal and the location of peaks"""
    t = data['t'].values
    # allow to either put a single value or a specific value for each moke signal
    if not isinstance(diff_reg, list):
        diff_reg = [diff_reg, diff_reg]
    if not isinstance(peak_prominence, list):
        peak_prominence = [peak_prominence, peak_prominence]
    if not isinstance(peak_height, list):
        peak_height = [peak_height, peak_height]
    peaks = dict()
    for i, key in enumerate(['moke1', 'moke2']):
        moke = data[key]
        deriv = TVRegDiff(moke, 5, diff_reg[i],
                          dx=t[1] - t[0], plotflag=False, diffkernel='sq')
        peaks[key], _ = find_peaks(
            np.abs(deriv), height=peak_height[i], prominence=peak_prominence[i])
        data[key + '_deriv'] = deriv
    return data, peaks


def clean_up_signal(raw_data, drop_frequencies=None, cutoff_freq=None, plot=False):
    # pad with 0 to speed up fft
    n_fft = next_fast_len(raw_data.shape[0])
    if plot:
        fig, ax = plt.subplots(3, 2, figsize=[6, 6])
        # also get the binned data so that we can compare the loops
        data_binned_before = get_averaged_loop(raw_data)
    for i, key in enumerate(['moke1', 'moke2']):
        # get the fft
        fft = np.fft.rfft(raw_data[key].values, n=n_fft, norm='ortho')
        freq = np.fft.rfftfreq(n_fft, d=1 / 10000)
        fft_abs = np.abs(fft)

        if plot:
            ax[0, i].set_title('Detector ' + str(i))
            ax[0, i].plot(freq[freq < 200], fft_abs[freq < 200])
            # set ylim based on the beak at 50Hz
            ylim = np.max(fft_abs[np.logical_and(freq > 40, freq < 60)]) * 1.5
            ax[0, i].set_ylim([0, ylim])
            for f in drop_frequencies:
                ax[0, i].plot(f * np.ones(10),
                              np.linspace(0, ylim, 10), alpha=0.4)
            ax[0, 0].set_ylabel('FFT before filter')

        if drop_frequencies is not None:
            for f in drop_frequencies:
                fft[np.logical_and(freq > f - 1, freq < f + 1)] = 0
        if cutoff_freq is not None:
            fft[freq > cutoff_freq] = 0
        ifft = np.fft.irfft(fft, n_fft, norm='ortho')
        raw_data[key] = ifft[:raw_data[key].shape[0]]

        if plot:
            fft_abs = np.abs(fft)
            ax[1, i].plot(freq[freq < 200], fft_abs[freq < 200])
            ax[1, i].set_ylim([0, ylim])
            ax[1, 0].set_ylabel('FFT after filter')

    if plot:
        for i, key in enumerate(['moke1', 'moke2']):
            data_binned_after = get_averaged_loop(raw_data)

            fields = data_binned_after.loc[:, ['Bx', 'By', 'Bz']]
            dir_vector = get_fields_dir_vector(data_binned_after)
            fields_dir = fields.dot(dir_vector)
            ax[2, i].plot(
                fields_dir, data_binned_before[key], label='Before', alpha=0.8)
            ax[2, i].plot(
                fields_dir, data_binned_after[key], label='After', alpha=0.8)
            ax[2, i].legend()
            ax[2, i].set_ylabel('MOKE')
        plt.tight_layout()
    return raw_data


def get_loop_integral(fields, moke, lims):
    """Integrates the loop over the given fields"""
    moke = np.array(moke)
    indx = np.logical_and(fields < lims[1], fields > lims[0])
    # get the fields step differences
    df = np.ediff1d(fields[indx])
    # get the moke signal pillars
    mkavg = (moke[indx][1:] + moke[indx][:-1]) / 2
    # get the integra;
    intg = np.sum(mkavg * df)
    return intg
