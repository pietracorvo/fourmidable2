from .calibrations import InstrumentCalibration
import numpy as np
import pandas as pd
import pickle
from numba import njit
from warnings import warn
from scipy.stats import binned_statistic


# @njit(fastmath=True, parallel=True, cache=True)
def update_hyst_line(L, x):
    """Function for updating the hysteresis line"""
    # first find out if we went up or down
    if L[-1, 0] < x:
        # we went up, get rid of the history of all elements that have alpha smaller than x
        L[L[:, 0] < x, 0] = x
        # add the newest element
        L = np.concatenate((L, np.array([[x, x]])), axis=0)
        # every other element needs to have a different alpha, otherwise need to get rid of it
        keep = np.zeros(L.shape[0]).astype(np.bool_)
        keep[0] = True
        keep[-1] = True
        for i in range(L.shape[0] - 2):
            if L[i, 0] != L[i + 1, 0]:
                keep[i] = True
                keep[i + 1] = True
        L = L[keep, :]
        return L
    if L[-1, 0] > x:
        # we went up, get rid of the history of all elements that have alpha smaller than x
        L[L[:, 1] > x, 1] = x
        # add the newest element
        L = np.concatenate((L, np.array([[x, x]])), axis=0)
        # every other element needs to have a different alpha, otherwise need to get rid of it
        keep = np.zeros(L.shape[0]).astype(np.bool_)
        keep[0] = True
        keep[-1] = True
        for i in range(L.shape[0] - 2):
            if L[i, 1] != L[i + 1, 1]:
                keep[i] = True
                keep[i + 1] = True
        L = L[keep, :]
        return L
    return L


def get_hystline_signal(L, F_fun):
    """Gets the value of the signal having the points of the Prezbiach line and the integral functions"""
    # get alphas and betas
    alpha, beta = L[:, 0], L[:, 1]
    # get all the horisontal lines
    indx_hor = (beta[1:] - beta[:-1]) != 0
#     lenh = np.sum(indx_hor)
#     print(lenh)
    # calcluate the signal
    signal = -F_fun(alpha[0], beta[0])
    F_kk = F_fun(alpha[:-1][indx_hor], beta[:-1][indx_hor])
    F_kk1 = F_fun(alpha[1:][indx_hor], beta[1:][indx_hor])
    signal += 2 * np.sum(F_kk - F_kk1)
    return signal


def reconstruct_hyst_signal(signal, L_start, F_fun):
    """Adjust for the hysteresis of the signal given the starting Preisach line
    and the integral F functions of the Preisach model"""
    # define the starting line
    L = np.array(L_start.copy()).astype(float)
    signal_out = np.zeros(len(signal))
    for i, x in enumerate(signal):
        L = update_hyst_line(L.copy(), float(x))
        signal_out[i] = get_hystline_signal(L, F_fun)
    return signal_out, L


def filter_signal(t, signal, bin_dt=0.005):
    # to speed up, filter the high frequency stuff
    signal_bin = binned_statistic(t, [t, signal], bins=int(
        (t[-1] - t[0]) / bin_dt), statistic='mean').statistic
    return signal_bin[0, :], signal_bin[1, :]


class MagnetHystCalib(InstrumentCalibration):
    """Rotates the input, inverts magnet core hysteresis  and applies RL circuit response to get the required voltages for the
    desired inputs.
    It adjusts for the hallprobe calibration so that when you say you want some fields in hallprobe readings,
    that's what you get.
    Uses Preisach model for hysteresis modelling. All parameters should be in one data folder together with the fits corresponding
    to minor and major loops

    Args:
        Parameters: full path to the file containing the calibration parameters. This should be in the data folder.
        Subinstruments: hallprobe, needed for getting the hallprobe calibration to invert to voltages.
    """

    def __init__(self, parameters, subinstruments):
        InstrumentCalibration.__init__(self, parameters)
        # get the hp calibration to be able to invert
        self.hallprobe = subinstruments
        assert parameters['kepco_mode'] in {'voltage', 'current'}
        self.kepco_mode = parameters['kepco_mode']
        # import the data
        self.file_path = parameters['file_path']
        # remove from parameters so that it doesn't interfere with saving
        del self.parameters['file_path']
        with open(self.file_path, 'rb') as fp:
            calibration_data = pickle.load(fp)

        # get the major loop fit
        self.main_branch_fits = calibration_data['main_branch']
        # get the minor loops fits
        self.transition_fits = calibration_data['transition_branches']
        # create F_functions of the Preisach model
        self.F_functions = [lambda a, b, f_a=f_a, f_ab=f_ab: (f_a.__call__(a) - f_ab.ev(a, b)) / 2
                            for f_a, f_ab in zip(self.main_branch_fits, self.transition_fits)]
        # list of poles, this is for convenience only
        self.poles = range(3)
        # get the per pole resistance
        self.R = calibration_data['R']
        # get the per pole inductance
        self.L = calibration_data['L']
        # get the Preisach line for degauss and the bounding line
        self.degauss_l = calibration_data['degauss_l']
        self.start_l = calibration_data['start_l']
        # define the cutoff frequency
        self.cutoff_freq = 100
        # # get the displacements of the fits (this should probably be 0's but still a small error in the fitting and this makes it a lot better)
        self.fitting_displacements = calibration_data['fitting_displacements']
        # get the maximum and minimum fields we can apply
        self.pole_mxmn = [self.start_l[pole][0, :] for pole in self.poles]

    def get_required_input_pole(self, t0, pole_signal, pole, repetitions=2):
        """Gets the required hex signal given the measured/desired hp signal for a given pole.
        hp_signal is expected to be nx2 array with first column being time.
        Returns the hx_signal"""

        F_fun = self.F_functions[pole]
        start_l = self.degauss_l[pole].copy()
        ds = self.fitting_displacements[pole]

        # to speed up, filter the high frequency stuff
        # (need to add minus because of how the calibration was done)
        t, signal = filter_signal(t0, pole_signal)
        n = signal.size
        timestep = t[1] - t[0]
        timestep0 = t0[1] - t0[0]

        # first invert the hysteresis. Do it repetitions time and create a full signal out of that
        signal_nohyst = np.zeros(signal.size * repetitions)
        t_nohyst = np.hstack([t + i * (t[-1] + timestep)
                              for i in range(repetitions)])
        t0_full = np.hstack([t0 + i * (t0[-1] + timestep0)
                             for i in range(repetitions)])
        for i in range(repetitions):
            signal_nohyst[i * n:(i + 1) * n], start_l = reconstruct_hyst_signal(
                signal, start_l, F_fun)
        # this is just to get the signal to 0 if the user gave zeros (instead of a very small displacement)
        signal_nohyst += ds

        # now adjust for the RL response if in V mode
        if self.kepco_mode == 'voltage':
            # do fft on the signal and extract the frequencies

            # get the pole parameters
            R = self.R[pole]
            L = self.L[pole]
            n = signal_nohyst.shape[0]
            fft = np.fft.rfft(signal_nohyst, norm='ortho')
            freq = np.fft.rfftfreq(n, d=timestep)
            # get the impedence
            Z = R + 1j * 2 * np.pi * freq * L

            # kill all of the ampilitudes of signals higher than 100Hz
            fft[freq > 100] = 0
            # get fft of voltage
            fft_v = fft * Z
            # invert fft, need to divide by 2 because when ni is applying 1V, the output is actually 2V
            v_pred = np.fft.irfft(fft_v, n=n, norm='ortho')
            v_pred /= 2
            # interpolate back to the original shape
            v_out = np.interp(t0_full, t_nohyst, v_pred)
        else:
            # interpolate back to the original shape
            v_out = np.interp(t0_full, t_nohyst, signal_nohyst)
        return v_out

    def get_required_input(self, t, fields, repetitions=2):
        """Gets the required hex signal given the measured/desired fields signal for a given pole.
        fields is expected to be nx3 array of the per-pole fields at the given time t.
        The t and fields array need to be the same length
        Returns the hx_signal in the same shape."""
        assert t.size == fields.shape[0]

        out_signal = np.zeros((fields.shape[0] * repetitions, fields.shape[1]))
        for pole in self.poles:
            out_signal[:, pole] = self.get_required_input_pole(
                t, fields[:, pole], pole, repetitions=repetitions)
        return out_signal

    def data2inst(self, data, return_setpoint=False, repetitions=2, return_transient=True, **kwargs):
        if data.shape[0] == 0:
            return data
        # invert hallprobe calibration (to get the fields in V)
        data_raw = self.hallprobe.calibration.data2inst(data)
        # get the time and fields for easier handling
        t = data_raw.index
        fields = data_raw.values
        # quickly check if the demanded fields are too large
        good_fields = self.check_fields(fields)
        if not good_fields:
            warn('Required fields too large!')

        # get the signal to output
        signal_out = self.get_required_input(
            t, fields, repetitions=repetitions)

        # make sure that the signal is capped by 10:
        if np.any(np.abs(signal_out) > 10):
            warn('Signal requires voltages beyond compliance!')
            signal_out[signal_out > 10] = 10
            signal_out[signal_out < -10] = -10

        # transform back into df
        signal_repetition = signal_out[-t.size:, :]
        if return_transient:
            timestep = t[1] - t[0]
            t_full = np.hstack([t + i * (t[-1] + timestep)
                                for i in range(repetitions)])
            data_out = [pd.DataFrame(signal_out, columns=data.columns,
                                     index=t_full),
                        pd.DataFrame(signal_repetition, columns=data.columns,
                                     index=t)
                        ]
        else:
            data_out = pd.DataFrame(signal_repetition, columns=data.columns,
                                    index=t)
        if return_setpoint:
            setpoint = {port: fields[:, i]
                        for i, port in enumerate(data.columns)}
            return data_out, setpoint
        else:
            return data_out

    def check_fields(self, fields):
        """Checks if the asked fields are out of range or not"""
        # check for every pole
        for pole in self.poles:
            # check if too positive
            if np.any(fields[:, pole] > self.pole_mxmn[pole][0]):
                return False
            # check if too negative
            if np.any(fields[:, pole] < self.pole_mxmn[pole][1]):
                return False
        return True


if __name__ == "__main__":
    calib_file = r'C:\Users\user\Documents\Python\MOKEpy\data\magnet_response_parameters_hyst.p'
    with open(calib_file, 'rb') as f:
        calib_data = pickle.load(f)
    start_l = calib_data['start_l']

    print(update_hyst_line(start_l[0], 1))
