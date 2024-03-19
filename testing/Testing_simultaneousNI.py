from instrumental.drivers.daq.ni import NIDAQ, Task
from instrumental import u
import numpy as np

from matplotlib import pyplot as plt

Rate = 1000
output_signal = 5*np.sin(np.linspace(0, 2*np.pi, Rate+1))
output_signal = np.delete(output_signal, len(output_signal)-1)


daq = NIDAQ('Dev1')
task = Task(daq.ao0, daq.ai7)
task.set_timing(duration='1s', fsamp='1000Hz')

write_data = {'ao0': output_signal * u.V}
result = task.run(write_data)

task.unreserve()
task.clear()

t = result['t']
rd = result['Dev1/ai7']
plt.plot(t, rd)
