import numpy as  np
import pandas as pd
import matplotlib.pyplot as plt

# generate a sine signal with some noise
amplitude = 5
period = 1
phase = 2*np.pi/5
# phase = 0
print('Inputs: ', amplitude, period, phase)
t = np.linspace(0, 3*period, 1000000)
signal = amplitude * np.cos(2*np.pi*t/period+phase)
n = signal.size
# signal += 0.01*np.random.rand(n)

timestep = t[1] - t[0]

# do the fourier transform on this signal
fft = np.fft.rfft(signal) / (n/2)

fft_phase = np.angle(fft)
fft_amp = np.absolute(fft)
freq = np.fft.rfftfreq(n, d=timestep)

# print out the frequency and amplitude max
i = np.array(fft_amp.argmax())
print('Amplitude: ', fft_amp[i])
print('Frequency: ', freq[i])
print('Phase: ', fft_phase[i])

plt.plot(t, signal)
# plt.show()

