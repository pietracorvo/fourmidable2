import matplotlib
import PyQt5

matplotlib.use('Qt5Agg')
from control.instruments.moke import Moke
import display.instrument_plotting as disp

import matplotlib.pyplot as plt
from matplotlib import animation
import experiments.basic as basic_experiments

import data.live_processing as processing

def live_plot(ax, device, *kwargs):
    # get the most recent data
    data = device.get_data()
    # get wollaston processed data
    woll_data = processing.wollaston_data(data[1:, :])
    # clear all the axes and then plot
    for key in ax:
        ax[key].clear()
        ax[key].plot(data[0], processing.smooth_data(woll_data[key]), label=key)
        ax[key].legend(loc="upper left", fancybox=True, framealpha=0.5)

mk = Moke()
# device = mk.instruments['wollaston']
# fig = plt.figure()
# ax = dict()
# ax['average'] = fig.add_subplot(211)
# ax['difference'] = fig.add_subplot(212)
#
# basic_experiments.sin_wave(mk)
# anim = disp.live_wollaston_plotting(fig, device, axes=ax)

# anim = animation.FuncAnimation(fig, lambda i: live_plot(ax, device), interval=int(1000 / 25))


device = mk.instruments['camera1']
fig = plt.figure()

ani = disp.live_camera(fig, device)

plt.show()
