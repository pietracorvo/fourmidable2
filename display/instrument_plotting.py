import numpy as np
import pyqtgraph as pg
from scipy.fftpack.helper import next_fast_len
import data.live_processing as processing
from PyQt5 import QtCore, QtWidgets
import traceback
import pandas as pd
from control.calibration import NIoffsetScale, HPSampleCalib

import time

COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class InstrumentPlotting:
    def __init__(self, device, plt, self_run=False):
        self.device = device
        if plt is None:
            self.plt = pg.plot(self.get_plot_data())
        else:
            self.plt = plt
            # self.plot()
        if self_run:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.plot)
            self.timer.start(50)
        else:
            self.timer = None

    def get_plot_data(self):
        data = self.device.get_data()
        return data

    def plot(self):
        data = self.get_plot_data()
        self.plt.clear()
        for i, c in enumerate(data):
            self.plt.plot(data.index, data[c], _callSync='off', pen=PENS[i])


class NIPlotting(InstrumentPlotting):
    def __init__(self, device, plt=None, plotting_time=5, legend=True, data_per_second=50, smooth_window=10, self_run=False):

        # how long the plot is going to keep the data for
        self.plotting_time = plotting_time
        # how many data points are plotted per second
        self.data_per_second = data_per_second
        self.smooth_window = smooth_window  # size of the smoothing window

        self.plotting_data = pd.DataFrame()
        self.first_run = True
        self.lines = dict()
        # self.plotting_data = self.update_plotting_data()

        # self.plt._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
        super().__init__(device, plt, self_run=self_run)
        if legend:
            self.legend = self.plt.addLegend()

    def get_plot_data(self, start_time=None):
        if start_time is None:
            start_time = np.max(
                (self.device.get_time() - self.plotting_time, 0))
        # get the most recent data
        data = self.device.get_data(start_time=start_time)
        if data.shape[0] != 0:
            time_interval = data.index[-1] - data.index[0]
            # if too few data, just continue
            if time_interval * self.data_per_second < 1:
                return pd.DataFrame(columns=data.columns)
            # get how many samples we are getting
            update_samples = int(self.data_per_second * time_interval)

            # get the data ready for plotting
            plotting_data = processing.prepare_for_plotting(
                data, update_samples, self.smooth_window)
        else:
            plotting_data = processing.prepare_for_plotting(
                data, 0, self.smooth_window)
        return plotting_data

    def update_plotting_data(self):
        # get the data and concat to the existing data
        if self.plotting_data.shape[0] != 0:
            start_new_data_time = self.plotting_data.index[-1]
            data = self.get_plot_data(
                start_time=start_new_data_time)
            if data.shape[0] == 0:
                return False
            self.plotting_data = pd.concat((self.plotting_data, data))
            # flush extra data
            self.plotting_data = self.plotting_data.loc[
                self.plotting_data.index > self.plotting_data.index[-1] - self.plotting_time]
        else:
            self.plotting_data = self.get_plot_data()
        return True

    def plot(self):
        updated = self.update_plotting_data()
        if not updated:
            return
        if self.plotting_data.shape[0] == 0:
            return
        clear = True
        # iterate over the columns and plot them
        for i, key in enumerate(self.plotting_data):
            if self.first_run:
                self.lines[key] = self.plt.plot(np.array(self.plotting_data.index),
                                                np.array(self.plotting_data[key]), clear=clear,
                                                pen=PENS[i], name=key)
            else:
                self.lines[key].setData(np.array(self.plotting_data.index),
                                        np.array(self.plotting_data[key]))
            clear = False
        self.first_run = False


class FFTplotting(InstrumentPlotting):
    def __init__(self, device, plt=None, plotting_time=1, cutoff_freq=150):
        super().__init__(device, plt)

        self.plotting_time = plotting_time

        self.first_run = True
        self.lines = dict()

        self.cutoff_freq = cutoff_freq
        self.last_update_time = 0

        self.sumdiff = False
        if self.device.name.split('_')[0][:-1] == 'wollaston':
            self.sumdiff = True

    def get_plot_data(self, start_time=None):
        if start_time is None:
            start_time = self.device.get_time() - self.plotting_time
        # get the most recent data
        data = self.device.get_data(start_time=start_time)
        if self.sumdiff:
            data['sum'] = data['det1'] + data['det2']
            data['diff'] = data['det1'] - data['det2']
        if data.shape[0] != 0:
            n = data.shape[0]
            n_fft = next_fast_len(n)
            # get the fft of data
            data_fft = np.abs(np.fft.rfft(np.array(data), n=n_fft, axis=0))
            # not interested in 0 frequency, so set to 0
            data_fft[0, :] = 0
            data_freq = np.fft.rfftfreq(n_fft, data.index[1] - data.index[0])

            # only select the data with the frequency smaller than the cut_off frequency
            fltr = data_freq < self.cutoff_freq
            data_fft = data_fft[fltr, :]
            data_freq = data_freq[fltr]
            plotting_data = pd.DataFrame(
                data_fft, columns=data.columns)
            plotting_data.index = data_freq
        else:
            plotting_data = pd.DataFrame(columns=data.columns)
        return plotting_data

    def plot(self):
        # if self.device.get_time() - self.last_update_time < self.plotting_time:
        #     return
        # self.last_update_time = self.device.get_time()
        plotting_data = self.get_plot_data()
        if plotting_data.shape[0] == 0:
            return
        clear = True
        # iterate over the columns and plot them
        for l in self.plt:
            if self.first_run:
                self.lines[l] = self.plt[l].plot(np.array(plotting_data.index),
                                                 np.array(plotting_data[l]), clear=clear,
                                                 pen=PENS[0], name=l)
                self.plt[l].showGrid(x=True)
            else:
                self.lines[l].setData(np.array(plotting_data.index),
                                      np.array(plotting_data[l]))
            clear = False
        self.first_run = False


class HPplotting(NIPlotting):
    def __init__(self, device, plt=None, plotting_time=0.5):
        super().__init__(device, plt=plt, legend=False,
                         data_per_second=50, plotting_time=plotting_time)

        ax_swap = np.array(((0, 1, 0), (1, 0, 0), (0, 0, -1)))
        ax_swap2 = np.array(((0, 0, 1), (0, 1, 0), (-1, 0, 0)))
        self.transform_m = np.transpose(ax_swap2.dot(ax_swap))
        # in case the HP calibration is in the plane of the sample, need to change the calibration used to be in the table frame
        if isinstance(device.calibration, HPSampleCalib):
            self.calibration = NIoffsetScale(
                {'scale': device.calibration.scale})
        else:
            self.calibration = device.calibration

    def get_plot_data(self, start_time=None):
        if start_time is None:
            start_time = self.device.get_time() - self.plotting_time
        # get the most recent data
        data = self.device.get_data(
            start_time=start_time, calibration=self.calibration)
        if data.shape[0] != 0:
            # get how many samples we are getting (aim for about 50 per second here)
            update_samples = int(self.data_per_second
                                 * (data.index[-1] - data.index[0]))
            # get the data ready for plotting
            plotting_data = processing.prepare_for_plotting(
                data, update_samples, self.smooth_window)
        else:
            plotting_data = processing.prepare_for_plotting(
                data, 0, self.smooth_window)
        return plotting_data

    def plot(self):
        self.update_plotting_data()
        if self.plotting_data.shape[0] == 0:
            return
        pts = self.plotting_data.values.dot(self.transform_m) / 5

        color = np.zeros([pts.shape[0], 4])
        color[:, 3] = np.linspace(0, 1, pts.shape[0])
        color[:, 0:3] = np.repeat(
            np.array([0, 1, 1])[None, :], pts.shape[0], axis=0)
        self.plt.setData(pos=pts, color=color, width=8, mode='line_strip')
        self.first_run = False


class WollastonPlotting(NIPlotting):
    def __init__(self, device, plt=None, **kwargs):
        """type can be difference or average"""
        super().__init__(device, plt=plt, legend=False, **kwargs)
        self.labels = ["difference", "average", "det1", "det2"]
        for p in self.plt.values():
            p.addLegend()
        assert isinstance(plt, dict)

    def update_plotting_data(self):
        if self.plotting_data.shape[0] != 0:
            # get the data and concat to the existing data
            data = self.get_plot_data(
                start_time=self.plotting_data.index[-1])
            # get wollaston processed data
            data = processing.wollaston_data(data)
            self.plotting_data = pd.concat((self.plotting_data, data))
            # flush extra data
            self.plotting_data = self.plotting_data.loc[
                self.plotting_data.index > self.plotting_data.index[-1] - self.plotting_time]
        else:
            data = self.get_plot_data()
            # get wollaston processed data
            self.plotting_data = processing.wollaston_data(data)

    def plot(self):
        self.update_plotting_data()
        if self.plotting_data.shape[0] == 0:
            return
        clear = True
        # iterate over the plots
        for l in self.labels:
            if self.first_run:
                self.lines[l] = self.plt[l].plot(np.array(self.plotting_data.index),
                                                 np.array(self.plotting_data[l]), clear=clear,
                                                 pen=PENS[0], name=l)
            else:
                self.lines[l].setData(np.array(self.plotting_data.index),
                                      np.array(self.plotting_data[l]))
            clear = False
        self.first_run = False


class CameraPlotting(InstrumentPlotting):
    def __init__(self, device, plt=None, view=None, crosshair=True):
        self.device = device

        if view is None:
            self.view = pg.GraphicsView()
            self.view.setAspectLocked(True)
        else:
            self.view = view
        if plt is None:
            self.plt = pg.ImageItem(border='w')
            self.view.addItem(self.plt)

        InstrumentPlotting.__init__(self, device, plt)

        if crosshair:
            self.vLine = pg.InfiniteLine(angle=90, movable=False, pen='k')
            self.hLine = pg.InfiniteLine(angle=0, movable=False, pen='k')
            self.view.addItem(self.vLine, ignoreBounds=True)
            self.view.addItem(self.hLine, ignoreBounds=True)
        self.first_plot = True
        self.crosshair = crosshair

        # if the camera is from instruments/camera_quantalux.py add also an extra panel with control buttons
        if hasattr(device, 'camera'):
            # TODO when moving camera dock i get an error
            input_exposuretime = QtWidgets.QSpinBox()
            input_exposuretime.setMinimum(device.exposure_time_range_us[0])
            input_exposuretime.setMaximum(device.exposure_time_range_us[1])
            input_exposuretime.setValue(device.exposure_time_us)
            def update_exposure_time():
                device.exposure_time_us = input_exposuretime.value()
            input_exposuretime.valueChanged.connect(update_exposure_time)
            label_framerate = QtWidgets.QLabel()
            def update_framerate():
                if isinstance(device.current_framerate, float):
                    label_framerate.setText(str(round(device.current_framerate, 3)))
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(update_framerate)
            self.timer.start(100)
            layout_input = QtWidgets.QGridLayout()
            layout_input.addWidget(QtWidgets.QLabel('Frames Per Second'), 1, 1)
            layout_input.addWidget(label_framerate, 1, 2)
            layout_input.addWidget(QtWidgets.QLabel('Exposure time [µs]'), 2, 1)
            layout_input.addWidget(input_exposuretime, 2, 2)
            # TODO
            #layout_input.addWidget(self.button_crop_camera_to_roi, 1, 3)
            #layout_input.addWidget(self.button_toggle_roi, 2, 3)
            layout_container = QtWidgets.QWidget()
            layout_container.setLayout(layout_input)
            self.view.scene().addWidget(layout_container)


    def get_plot_data(self):
        return self.device.get_data()

    def plot(self):
        data = np.rot90(self.get_plot_data(), k=3).astype(np.uint8)
        if self.first_plot and self.crosshair:
            self.vLine.setPos(data.shape[0] / 2)
            self.hLine.setPos(data.shape[1] / 2)
        self.plt.setImage(data, autoDownsample=False)
        self.first_plot = False


class MokePlotting(InstrumentPlotting):
    def __init__(self, moke, layout):
        self.layout = layout

        self.plotting_instruments = [
            "hallprobe",
            "temperature",
            # "bighall_fields",
            # "bighall_temp",
            "hexapole",
            "nanocube",
            "wollaston_difference",
            "wollaston_average",
            "wollaston_det1",
            "wollaston_det2"
        ]

        self.plt = dict()
        for i, name in enumerate(self.plotting_instruments):
            self.plt[name] = self.layout.addPlot(title=name)
            if i == 3:
                self.layout.nextRow()

        self.inst_plotting = dict()
        try:
            self.inst_plotting["hallprobe"] = NIPlotting(
                moke.instruments["hallprobe"], plt=self.plt["hallprobe"])
            self.inst_plotting["temperature"] = NIPlotting(
                moke.instruments["temperature"], plt=self.plt["temperature"], plotting_time=300,
                data_per_second=1)
            # self.inst_plotting["bighall_fields"] = NIPlotting(moke.instruments["bighall_fields"],
            #                                                   plt=self.plt["bighall_fields"])
            # self.inst_plotting["bighall_temp"] = NIPlotting(moke.instruments["bighall_temp"],
            #                                                 plt=self.plt["bighall_temp"], plotting_time=300,
            #                                                 data_per_second=1)
            self.inst_plotting["hexapole"] = NIPlotting(moke.instruments["hexapole"],
                                                        plt=self.plt["hexapole"])
            self.inst_plotting["nanocube"] = NIPlotting(moke.instruments["nanocube"],
                                                        plt=self.plt["nanocube"])

            self.inst_plotting["wollaston"] = WollastonPlotting(moke.instruments["wollaston"],
                                                                plt={
                                                                    "difference": self.plt["wollaston_difference"],
                                                                    "average": self.plt["wollaston_average"],
                                                                    "det1": self.plt["wollaston_det1"],
                                                                    "det2": self.plt["wollaston_det2"]
            })

            InstrumentPlotting.__init__(self, moke, plt=self.plt)
        except:
            traceback.print_exc()

    def plot(self):
        for key, inst in self.inst_plotting.items():
            inst.plot()

    def get_plot_data(self):
        pass
