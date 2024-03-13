import numpy as np
from scipy.signal import chirp

# TODO: write the convention


def deGaussing_fun(t):
    t_length = t[-1] - t[0]
    amp_start = 2.5
    assert t_length > 1, 'deGaussing has to last more than a second'
    signal = chirp(t, f0=1, f1=20, t1=t[-1], method='quadratic', phi=90)
    # get the length of a signal before 1s from start
    l = len(t[t < t[0] + 1])
    amplitude = np.hstack((amp_start * np.ones(int(l)),
                           np.linspace(amp_start, 0, int(len(t) - l))))
    signal = np.multiply(signal, amplitude)
    return signal


def get_deGaussing_fun():
    return deGaussing_fun


def get_deGaussing_signal():
    return [get_deGaussing_fun()] * 3


def get_const_fun(constant):
    return lambda t: constant * np.ones(len(t))


def get_const_signal(constants):
    return [get_const_fun(c) for c in constants]


# def zeros_signal():
#     function_list = [
#         lambda x: np.zeros(len(x)),
#         lambda x: np.zeros(len(x)),
#         lambda x: np.zeros(len(x))
#     ]
#     return function_list


def get_zeros_signal():
    """Returns all zeros signal"""
    function_list = [
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x))
    ]
    return function_list


def get_cube_points(side_length, resolution):
    """Gets the points of a cube in a list which can be iterated over.

    Care is taken to take the most efficient path to save time

        Args:
            side_length (num): length of cube side
            resolution (num): distance between points

        Returns:
            points (ndarray): Nx3 matrix containing a list of points
    """

    side = np.linspace(0, side_length, np.floor(side_length / resolution) + 1)
    y, z, x = np.meshgrid(side, side, side)
    # flip every odd row of x
    x[:, 1::2, :] = np.flip(x[:, 1::2, :], 2)
    # same with y, but with different component
    y[1::2, :, :] = np.flip(y[1::2, :, :], 1)

    points = np.array([[i, j, k] for i, j, k in zip(
        x.flatten(), y.flatten(), z.flatten())])
    return points


def stack_funs(signals_list, period_list):
    """Stacks signals with their periods into a large signal with multiple periods"""

    def signal_fun(t_vector, signals_list, period_list):
        period_cumsum = t_vector[0] + np.hstack(([0], np.cumsum(period_list)))
        period_cumsum[-1] = np.inf
        signal = np.concatenate(
            [signals_list[i](t_vector[(period_cumsum[i] <= t_vector) & (t_vector < period_cumsum[i + 1])] - period_cumsum[i])
             for i in range(len(period_list))])
        return signal

    def f(t): return signal_fun(t, signals_list, period_list)
    total_period = np.sum(period_list)
    return f, total_period


# TODO: document this
def field_mapping_signal(degauss_time, stage_move_time, field_acquisition_time, field_buffer_time, field_strength):
    """"""
    ds_time = np.max([degauss_time, stage_move_time]
                     )  # max time between degaussing and stage motion
    magnet_funs = []
    funcs = [
        get_deGaussing_fun(),
        get_const_fun(0),
        get_const_fun(field_strength)
    ]  # same for every magnet, periods vary
    for i in range(3):
        periods = [
            degauss_time,
            ds_time - degauss_time + 1 + i *
            (field_acquisition_time + field_buffer_time),
            (field_buffer_time + field_acquisition_time) * (3 - i)
        ]
        f, total_period = stack_funs(funcs, periods)
        magnet_funs.append(f)

    return magnet_funs, total_period


def get_sin_fun(amplitude, period, phase, offset=0):
    return lambda x, amplitude=amplitude, period=period, phase=phase: amplitude * np.sin(np.pi * 2 * x / period + np.deg2rad(phase)) + offset


def get_sin_signal(amplitudes, periods, phases=(0, 0, 0), offsets=(0, 0, 0)):
    """Returns a sin signal with given amplitudes, periods and phases given in array

    Args:
        amplitudes (iterable): per magnet amplitude
        periods (iterable, num): per magnet period. If just a single number is given, it is assumed that all periods are equal

    Kwargs:
        phases (iterable): per magnet phase
    """
    # also support just one period if you want them to all be equal
    if not isinstance(periods, list):
        periods = [periods] * 3
    assert len(amplitudes) == 3 and len(offsets) == 3 and len(
        phases) == 3, 'Wrong number of inputs'
    return [get_sin_fun(a, per, ph, offset=off) for a, per, ph, off in zip(amplitudes, periods, phases, offsets)]


def random_signal_fun(t, cutoff_freq=100, min_amp=0.01, max_amp=10):
    """Defines a random signal function with cutoff frequency and minimum amplitude"""
    rate = int(1 / (t[1] - t[0]))
    n_samples = t.size
    if n_samples % 2 == 0:
        ft_length = int(n_samples / 2 + 1)
    else:
        ft_length = int((n_samples + 1) / 2)
    freq = np.fft.rfftfreq(n_samples, 1 / rate)
    # put in a random amplitude and phase
    fft_amp = np.random.rand(ft_length)
    fft_phase = np.random.rand(ft_length) * 2 * np.pi
    # filter out the amplitudes with frequencies above the cutoff frequency
    fft_amp = fft_amp * (freq < cutoff_freq)
    fft_signal = fft_amp * np.exp(1j * fft_phase)
    signal = np.fft.irfft(fft_signal, n=n_samples)

    # scale the signal so that it is between 0 and 10signal
    signal /= np.max(np.abs(signal))
    signal *= np.random.beta(2, 2) * (max_amp - min_amp) + min_amp
    return signal


def get_random_signal(cutoff_freq=100, min_amp=0.01, max_amp=10):
    """Gets random signal defined by get_random_function for all three magnets separately"""
    return [lambda t: random_signal_fun(t, cutoff_freq, min_amp, max_amp)] * 3
