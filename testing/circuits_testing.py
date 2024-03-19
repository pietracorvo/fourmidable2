
import pyqtgraph as pg
import numpy as np
import pandas as pd
from circuits import Event, Timer, Component
import time
COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class InstrumentPlotting(Component):
    def __init__(self, device, plt=None):
        super().__init__(self)
        self.device = device
        if plt is None:
            self.plt = pg.plot()
        else:
            self.plt = plt
        self.plot()
        Timer(0.5, Event.create('plot'), persist=True).register(self)
        self.run()

    def get_plot_data(self):
        data = self.device.get_data()
        return data

    def plot(self):
        data = self.get_plot_data()
        self.plt.clear()
        for i, c in enumerate(data):
            self.plt.plot(data.index, np.array(
                data[c].values), _callSync='off', pen=PENS[i])
        time.sleep(0.2)


class RandomDevice():
    def __init__(self):
        self.time = np.linspace(0, np.pi * 2, 100)
        self.data = np.sin(self.time)
        self.current_index = 0
        self.index_step = 10

    def get_data(self):
        indx = np.arange(self.current_index,
                         self.current_index + self.index_step)
        data_out = np.take(self.data, indx, mode='wrap')
        time_out = np.take(self.time, indx, mode='wrap')
        self.current_index += self.index_step
        return pd.DataFrame(data_out, index=time_out)


if __name__ == "__main__":
    app = pg.QtGui.QApplication([])

    device = RandomDevice()
    plotting = InstrumentPlotting(device)
    pg.QtGui.QApplication.exec_()
