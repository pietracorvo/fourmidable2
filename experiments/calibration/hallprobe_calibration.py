import numpy
import numpy as np
import matplotlib.pyplot as plt
import h5py
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from experiments.basic import deGauss
from data.signal_generation import get_zeros_signal
from control.calibration.calibrations import InstrumentCalibration
import time
from data.hallprobe_calibration import get_hallprobe_calibration
from experiments.basic import zero_magnet


def get_random_signal(t, cutoff_freq, min_amp=0.25):
    rate = int(1 / (t[1] - t[0]))
    n_samples = t.size

    if n_samples % 2 == 0:
        ft_length = int(n_samples / 2 + 1)
    else:
        ft_length = int((n_samples + 1) / 2)
    freq = np.fft.rfftfreq(n_samples, 1 / rate)
    # put in a random amplitude and phase over the relevant frequencies
    fft_amp = np.zeros(ft_length)
    fft_phase = np.zeros(ft_length)
    fltr = (freq < cutoff_freq)
    fltr_len = np.sum(fltr)
    fft_amp[fltr] = np.random.beta(1, 3, fltr_len)
    fft_phase[fltr] = np.random.rand(fltr_len) * 2 * np.pi
    # filter out the amplitudes with frequencies above the cutoff frequency
    fft_amp = fft_amp * (freq < cutoff_freq)
    fft_signal = fft_amp * np.exp(1j * fft_phase)
    signal = np.fft.irfft(fft_signal, n=n_samples)

    # scale the signal so that it is between 0 and 9
    signal *= 9 / np.max(np.abs(signal))

    return signal


def calibrate_hallprobe(moke, period=5, cutoff_freq=5, plot=False):
    hp = moke.instruments['hallprobe']
    bighp = moke.instruments['bighall_fields']
    magnet = moke.instruments['hexapole']
    #stage = moke.instruments['stage']
    # make sure the calibration is default
    # set the flushing time to be appropriate
    magnet.flushing_time = np.max([period + 1, 10])
    hp.flushing_time = np.max([period + 1, 10])
    bighp.flushing_time = np.max([period + 1, 10])
    # set the calibration to be default for both the magnet and the hallprobes, but not the big hallprobe
    magnet.calibration = InstrumentCalibration()
    hp.calibration = InstrumentCalibration()

    # get the signal generating function
    signal = [lambda t: get_random_signal(t, cutoff_freq)] * 3
    #numpy.savetxt("C:/Users/3Dstation3/Desktop/RandomSignal.csv", signal)
    # degauss and apply the random signal
    deGauss(moke)
    start_time = magnet.stage_data(signal, period, use_calibration=False) - 0.5
    end_time = start_time + period + 0.5

    # open a file in which to write
    print('Applying test field')
    filename = 'HallprobeCalib_' + time.strftime("%Y%m%d-%H%M") + '.h5'
    with h5py.File(filename, 'w') as file:
        magnet.save(file, start_time=start_time, end_time=end_time,
                    wait=True)
        hp.save(file, start_time=start_time, end_time=end_time,
                wait=True)
        bighp.save(file, start_time=start_time, end_time=end_time, wait=True)
        #stage.save(file)
    print('Data acquired')
    zero_magnet(moke)

    # calculate the calibration
    result, pred, data = get_hallprobe_calibration(filename, plot=plot)
    return result, pred, data


if __name__ == "__main__":
    from control.instruments.moke import Moke

    with Moke() as moke:
        calibrate_hallprobe(moke, plot=True)
        print('!!! NOTABENE !!!\nAfter HP recalibration you might need to tweak the PID parameter "Mean error HP stop criterion"')
