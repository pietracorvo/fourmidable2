import numpy as np
import pandas as pd
from scipy.stats import binned_statistic
from scipy.fftpack import next_fast_len


def filter_signal(timestep, signal, cutoff_freq=100):
    # to speed up, filter the high frequency stuff
    n = signal.shape[0]
    n_fft = next_fast_len(n)
    fft = np.fft.rfft(signal, n=n_fft, axis=0)
    freq = np.fft.rfftfreq(n_fft, d=timestep)
    print('setting to 0')
    print(cutoff_freq)
    fft[freq > cutoff_freq, :] = 0
    signal_filtered = np.fft.irfft(fft, n=n, axis=0)
    return signal_filtered


def filter_signal_pd(signal, cutoff_freq=100):
    t = signal.index
    values = signal.values
    print('filtering')
    values = filter_signal(t[1] - t[0], values, cutoff_freq=cutoff_freq)
    return pd.DataFrame(values, columns=signal.columns, index=t)
