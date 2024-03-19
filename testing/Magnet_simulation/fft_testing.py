import numpy as np
import matplotlib.pyplot as plt

# create a signal
time_l = 3
rate = 10000
t = np.arange(0, 3, 1/rate)
signal = np.zeros(t.size)
signal[t>0.5 & t<1.5] = 1
plt.plot(signal)