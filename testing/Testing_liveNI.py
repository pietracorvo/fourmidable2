from instrumental.drivers.daq.ni import NIDAQ, Task
from instrumental import u
import numpy as np
import matplotlib.animation as animation
from matplotlib import pyplot as plt

from numpy.core.multiarray import ndarray


def animate(i):
    if hasattr(animate, 't') and hasattr(animate, 'rd'):
        # num_samples = Rate/fps
        # frac_signal = output_signal[np.mod(np.int(i*num_samples), Rate):np.mod(np.int((i+1)*num_samples), Rate)]
        result = task.read()
        if animate.t.size == 0:
            animate.t = np.array(result['t'])
        else:
            animate.t = np.append(animate.t, 1/Rate+animate.t[-1]+np.array(result['t']))

        # if not all(result['Dev1/port0/line7']):
        #     print(result['Dev1/port0/line7'][-1])
        animate.rd = np.append(animate.rd, result['Dev1/port0/line7'])
        # print(animate.rd)
        disp_time = 5
        if len(animate.t) > disp_time*Rate:
            t = animate.t[len(animate.t)-disp_time*Rate:]
            rd = animate.rd[len(animate.rd)-disp_time*Rate:]
        else:
            t = animate.t
            rd = animate.rd

        ax.clear()
        # print(np.shape(t))
        # print(np.shape((rd)))
        ax.plot(t, rd)
    else:
        animate.t = np.array([])
        animate.rd = np.array([])


Rate = 10000
fps = 50
output_signal = 5*np.sin(np.linspace(0, 2*np.pi, Rate+1))
output_signal = np.delete(output_signal, len(output_signal)-1)
fig = plt.figure()
ax = plt.subplot(111)

plt.tick_params(labelsize=18)


daq = NIDAQ('Dev1')

# task = Task(daq.ao1, daq.ai7, daq.ai17)
prt = daq.port0[7].as_input()
task = Task(prt, daq.ai7, daq.ai17)
task.set_timing(fsamp='1000Hz', n_samples=100, mode='continuous')
# write_data = {'ao1': output_signal * u.V}
# task.write(write_data, autostart=False)

task.start()
ani = animation.FuncAnimation(fig, animate, interval=1000/fps)
plt.show()

task.stop()
