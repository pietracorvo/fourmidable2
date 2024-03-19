#  Testing the fft algorithms in python
#  Dedalo Sanz.

import numpy as np
import matplotlib.pyplot as plt

# Number of sample points
N = 2**11
# sample spacing
T = 1.0 / 800.0
# time vector
x = np.linspace(0.0, N*T, N)
# test signal
y = 20 * np.sin(25.0*2*np.pi*x+np.pi) + 30*np.sin(80.0 * 2.0*np.pi*x+np.pi/2)+np.random.rand(N)-0.5

# amplitude transform, unnormalized (by number of samples)
yf = np.fft.rfft(y)
# amplitude transform, normalized for display (ifft requires the unnormalized transform)
yfn = 2*yf/N

# frequency axis matching the fft results
xf = np.fft.rfftfreq(y.shape[0],T)

# inverse fft check
iy = np.fft.irfft(yf)
# scaling the frequency components has the expected result in the real transform.
# half the frequency spectrum results in half the amplitude in the time series
iy2 = np.fft.irfft(yf/2*np.exp(1j*np.pi))
plt.figure(1)
plt.plot(x, iy)
plt.plot(x, iy2)


yf2 = np.fft.rfft(y/2)

plt.figure(2)
plt.plot(xf, np.abs(yfn))
plt.plot(xf, 2*np.abs(yf2)/N)


plt.figure(2)
plt.plot(xf, np.angle(yf, deg=True))
plt.grid()

plt.grid()

plt.show()