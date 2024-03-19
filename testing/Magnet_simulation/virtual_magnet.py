# This scripts simulates the response of an electromagnet to an input signal
# this response consits on:
#   1. A frequency dependent amplitude response
#   2. A frequency dependent phase shift
#   3. Saturation at high signal amplitude

import numpy as np
import matplotlib.pyplot as plt


def amp_res(F_Hz=np.array([0.0, 0.0])):
    return np.exp(-F_Hz / 100 + 1) / np.exp(1)


def phase_shift_rad(F_Hz=np.array([0.0, 0.0])):
    return 2*np.pi * np.exp(-F_Hz / (500) + 1) / np.exp(1)

#print(phase_shift_rad(0.0) * 360 / 2 / 3.1415)


def saturation(A=np.array([0.0, 0.0])):
    return np.tanh(A*1.5)


def NI_clipping(signal=np.array([0.0, 0.0])):
    signal[signal > 1] = 1
    signal[signal < -1] = -1
    return signal


def magnet_response(dt, signal=np.array([0.0, 0.0])):
    N = signal.shape[0]
    # NI clipping considered
    signal = NI_clipping(signal)
    # signal transform (ifft requires the unnormalized transform)
    sf = np.fft.rfft(signal)
    # frequency axis matching the fft results [Hz]
    xf = np.fft.rfftfreq(signal.shape[0], dt)
    # response in fourier space without saturation
    rf = sf*amp_res(xf)*np.exp(1j * phase_shift_rad(xf))
    # signal back in the time domain
    st = np.fft.irfft(rf)
    return saturation(st)


# f_vector = np.linspace(0.0, 500*2*np.pi, 1000)
# t_vector = np.linspace(0.0,10,1000)
# plt.figure(2)
# plt.plot(f_vector/2/np.pi, amp_res(f_vector))
# plt.figure(1)
# plt.plot(f_vector / 2 / np.pi, phase_shift_rad(f_vector))
# plt.figure(3)
# plt.plot(t_vector, saturation(3*np.sin(t_vector)))
#
#
# total_t = 10
# S_rate = 10000
# t_vector = np.linspace(0.0,total_t,total_t*S_rate)
#
# dt = 1/S_rate
# signal = 0.6*np.sin(2*np.pi*t_vector)+0.3*np.sin(6*2*np.pi*t_vector+np.pi/3) + np.sin(200*2*np.pi*t_vector+np.pi/3)
#
#
# plt.figure(4)
# plt.plot(t_vector, signal)
# plt.plot(t_vector, NI_clipping(signal))
# plt.plot(t_vector, magnet_response(dt, signal))
# plt.show()
