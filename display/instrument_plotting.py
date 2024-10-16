import numpy as np
import pyqtgraph as pg
from scipy.fftpack.helper import next_fast_len
import data.live_processing as processing
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIcon
import traceback
import pandas as pd
from control.calibration import NIoffsetScale, HPSampleCalib
from PyQt5.QtWidgets import *
import pyqtgraph as pg

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

class CameraLivePlotting(InstrumentPlotting):
    def __init__(self, device, view=None, crosshair=True):
        self.device = device

        if view is None:
            self.view = pg.GraphicsLayoutWidget()
        else:
            self.view = view
        self.plot1 = self.view.addPlot(row=0, col=0)
        self.plot1.setAspectLocked(True)
        self.plot1.hideAxis('bottom')
        self.plot1.hideAxis('left')
        self.image = pg.ImageItem()
        self.plot1.addItem(self.image)
        self.plot2 = self.view.addPlot(row=1, col=0)
        self.plot2.setLogMode(False, True)
        self.plot2.hide()

        InstrumentPlotting.__init__(self, device, self.image)

        if crosshair:
            self.vLine = pg.InfiniteLine(angle=0, movable=False, pen='k')
            self.hLine = pg.InfiniteLine(angle=90, movable=False, pen='k')
            self.plot1.addItem(self.vLine)
            self.plot1.addItem(self.hLine)
        self.first_plot = True
        self.crosshair = crosshair

        # Create the menu layout with buttons
        self.create_menu()

    def create_menu(self):
        """Creates the menu layout with buttons for the histogram and camera settings."""
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout()

        # Button to show/hide the histogram
        self.histogram_button = QPushButton()
        icon_path = r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\hist.png"
        self.histogram_button.setIcon(QIcon(icon_path))
        self.histogram_button.setCheckable(True)
        self.histogram_button.clicked.connect(self.button_hide_show_histogram)
        self.menu_layout.addWidget(self.histogram_button)

        # Button for camera settings (functionality can be extended later)
        self.settings_button = QPushButton()
        icon_path2 = r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\clock.png"
        self.settings_button.setIcon(QIcon(icon_path2))
        self.settings_button.clicked.connect(self.open_camera_settings)
        self.menu_layout.addWidget(self.settings_button)

        # Add a stretch to push buttons to the top
        self.menu_layout.addStretch(1)

        # Set the layout to the menu widget
        self.menu_widget.setLayout(self.menu_layout)

    def button_hide_show_histogram(self):
        """Toggle the visibility of the histogram plot."""
        if self.histogram_button.isChecked():
            self.plot2.show()
        else:
            self.plot2.hide()

    def open_camera_settings(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def get_menu_widget(self):
        """Returns the menu widget to be added to the layout."""
        return self.menu_widget

    def button_hide_show_histogram(self):
        if self.histogram_button.isChecked():
            self.plot2.show()
        else:
            self.plot2.hide()

    def update_framerate(self):
        try:
            if isinstance(self.device.current_framerate, float):
                self.label_framerate.setText(str(round(self.device.current_framerate, 3)))
        except:
            pass

    def get_plot_data(self):
        img = self.device.get_data()
        self.update_framerate()
        return img

    def plot(self):
        self.first_plot = False
        data = self.get_plot_data()
        if self.crosshair:
            self.vLine.setPos(data.shape[0] / 2)
            self.hLine.setPos(data.shape[1] / 2)
        self.image.setImage(data, axisOrder='row-major', autoDownsample=False,
                            border=(169,169,169))
        hist, bins = np.histogram(data.flatten(), bins='auto')
        self.plot2.plot(bins[:-1], hist, clear=True)
        self.plot2.setTitle(f'<h3>Mean   {round(np.mean(data),1)}<br>Median {np.median(data)}<h3>')

class CameraStaticPlotting(InstrumentPlotting):
    def __init__(self, device, view=None, crosshair=True):
        self.device = device

        if view is None:
            self.view = pg.GraphicsLayoutWidget()
        else:
            self.view = view
        self.plot1 = self.view.addPlot(row=0, col=0)
        self.plot1.setAspectLocked(True)
        self.plot1.hideAxis('bottom')
        self.plot1.hideAxis('left')
        self.image = pg.ImageItem()
        self.plot1.addItem(self.image)
        self.plot2 = self.view.addPlot(row=1, col=0)
        self.plot2.setLogMode(False, True)
        self.plot2.hide()

        InstrumentPlotting.__init__(self, device, self.image)

        if crosshair:
            self.vLine = pg.InfiniteLine(angle=0, movable=False, pen='k')
            self.hLine = pg.InfiniteLine(angle=90, movable=False, pen='k')
            self.plot1.addItem(self.vLine)
            self.plot1.addItem(self.hLine)
        self.first_plot = True
        self.crosshair = crosshair

        # Create the menu layout with buttons
        self.create_menu()

    def create_menu(self):
        """Creates the menu layout with buttons for the histogram and camera settings."""
        self.menu_widget = QWidget()
        self.menu_layout = QVBoxLayout()

        # Button to show/hide the histogram
        self.photo_button = QPushButton()
        self.photo_button.setIcon(QIcon(r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\photo.png"))
        # self.photo_button.clicked.connect(self.button_take_photo)
        self.menu_layout.addWidget(self.photo_button)

        # Button for camera settings (functionality can be extended later)
        self.save_button = QPushButton()
        self.save_button.setIcon(QIcon(r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\save.png"))
        self.save_button.clicked.connect(self.button_save_photo)
        self.menu_layout.addWidget(self.save_button)

        # Button for camera settings (functionality can be extended later)
        self.video_button = QPushButton()
        self.video_button.setIcon(QIcon(r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\video.png"))
        self.video_button.clicked.connect(self.button_save_video)
        self.menu_layout.addWidget(self.video_button)

        # Button for camera settings (functionality can be extended later)
        self.upload_image = QPushButton()
        self.upload_image.setIcon(QIcon(r"C:\Users\3DStation4\PycharmProjects\pythonProject_3DMOKE_new\gui\widgets\icons\upload.png"))
        self.upload_image.clicked.connect(self.button_upload_image)
        self.menu_layout.addWidget(self.upload_image)

        # Add a stretch to push buttons to the top
        self.menu_layout.addStretch(1)

        # Set the layout to the menu widget
        self.menu_widget.setLayout(self.menu_layout)


    def button_take_photo(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def button_save_photo(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def button_save_video(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def button_upload_image(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")


    def button_take_photo(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def button_take_photo(self):
        """Opens camera settings (placeholder, extend functionality as needed)."""
        QMessageBox.information(self.view, "Camera Settings", "Camera settings dialog placeholder")

    def get_menu_widget(self):
        """Returns the menu widget to be added to the layout."""
        return self.menu_widget



    def button_hide_show_histogram(self):
        if self.button.isChecked():
            self.plot2.show()
        else:
            self.plot2.hide()

    def update_framerate(self):
        try:
            if isinstance(self.device.current_framerate, float):
                self.label_framerate.setText(str(round(self.device.current_framerate, 3)))
        except:
            pass

    def get_plot_data(self):
        img = self.device.get_data()
        self.update_framerate()
        return img

    def plot(self):
        self.first_plot = False
        data = self.get_plot_data()
        if self.crosshair:
            self.vLine.setPos(data.shape[0] / 2)
            self.hLine.setPos(data.shape[1] / 2)
        self.image.setImage(data, axisOrder='row-major', autoDownsample=False,
                            border=(169,169,169))
        hist, bins = np.histogram(data.flatten(), bins='auto')
        self.plot2.plot(bins[:-1], hist, clear=True)
        self.plot2.setTitle(f'<h3>Mean   {round(np.mean(data),1)}<br>Median {np.median(data)}<h3>')


class CameraPlotting(InstrumentPlotting):
    def __init__(self, device, view=None, crosshair=True):
        self.device = device

        if view is None:
            self.view = pg.GraphicsLayoutWidget()
        else:
            self.view = view
        self.plot1 = self.view.addPlot(row=0, col=0)
        self.plot1.setAspectLocked(True)
        self.plot1.hideAxis('bottom')
        self.plot1.hideAxis('left')
        self.image = pg.ImageItem()
        self.plot1.addItem(self.image)
        self.plot2 = self.view.addPlot(row=1, col=0)
        self.plot2.setLogMode(False, True)
        self.plot2.hide()

        InstrumentPlotting.__init__(self, device, self.image)

        if crosshair:
            self.vLine = pg.InfiniteLine(angle=0, movable=False, pen='k')
            self.hLine = pg.InfiniteLine(angle=90, movable=False, pen='k')
            self.plot1.addItem(self.vLine)
            self.plot1.addItem(self.hLine)
        self.first_plot = True
        self.crosshair = crosshair

        # TODO maybe give it an own plotting thread, long exposure times makes gui laggy
        self.label_framerate = QtWidgets.QLabel()
        layout_input = QtWidgets.QGridLayout()
        self.button = QtWidgets.QPushButton('Histogram')
        self.button.setCheckable(True)
        self.button.clicked.connect(self.button_hide_show_histogram)
        layout_input.addWidget(QtWidgets.QLabel('Frames Per Second'), 1, 1)
        layout_input.addWidget(self.label_framerate, 1, 2)
        layout_input.addWidget(self.button, 2, 1)
        layout_container = QtWidgets.QWidget()
        layout_container.setLayout(layout_input)
        self.view.scene().addWidget(layout_container)

    def button_hide_show_histogram(self):
        if self.button.isChecked():
            self.plot2.show()
        else:
            self.plot2.hide()

    def update_framerate(self):
        try:
            if isinstance(self.device.current_framerate, float):
                self.label_framerate.setText(str(round(self.device.current_framerate, 3)))
        except:
            pass

    def get_plot_data(self):
        img = self.device.get_data()
        self.update_framerate()
        return img

    def plot(self):
        self.first_plot = False
        data = self.get_plot_data()
        if self.crosshair:
            self.vLine.setPos(data.shape[0] / 2)
            self.hLine.setPos(data.shape[1] / 2)
        self.image.setImage(data, axisOrder='row-major', autoDownsample=False,
                            border=(169,169,169))
        hist, bins = np.histogram(data.flatten(), bins='auto')
        self.plot2.plot(bins[:-1], hist, clear=True)
        self.plot2.setTitle(f'<h3>Mean   {round(np.mean(data),1)}<br>Median {np.median(data)}<h3>')


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
