from PyQt5.QtWidgets import *
from pyqtgraph.dockarea import *
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from control.instruments import NIinst
from display.instrument_plotting import *
from gui.widgets.canvas import DynamicHPPlot
from gui.widgets.console_widget import ConsoleWidget
from functools import partial

import sys
from PyQt5.QtWidgets import QApplication


def start_application(moke, dock_list):
    """Starts the moke docker application. The dock list is a list of wanted docks. Possibilities are:

        (all instrument names)
        wollaston1_composite
        wollaston2_composite
        3D_fields
        console
        wollaston1_fft
        wollaston2_fft
    """
    # start plotting
    app = QApplication(sys.argv)
    aw = MokeDocker(moke, dock_list=dock_list)
    aw.show()
    app.exec_()


class MokeDocker(QWidget):
    # add a signal when docks get closed
    sigDockClosed = QtCore.pyqtSignal(str)

    def __init__(self, moke, dock_list=None, framerate=20):
        self.framerate = framerate
        self.moke = moke
        QWidget.__init__(self)
        self.dockarea = DockArea()

        # get a list of NI instruments
        self.ni_instruments = [
            key for key, value in self.moke.instruments.items() if isinstance(value, NIinst)]
        # list of NI instruments to add as docks:
        if dock_list is None:
            self.dock_names = [
                "hallprobe",
                "temperature",
                "hexapole",
                "wollaston1_composite",
                "camera1",
                "camera2",
                # "3D_fields"
                "console"
            ]
        else:
            self.dock_names = dock_list

        self.dock_dict = dict()
        self.dynamic_plots = dict()
        for name in self.dock_names:
            self.add_dock(name)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)

        # add the layout
        layout = QHBoxLayout()
        layout.addWidget(self.dockarea)
        self.setLayout(layout)
        self.start_timer()

    def add_dock(self, name):
        try:
            if name in self.ni_instruments:
                plt = pg.PlotWidget(title=name)
                if 'temp' not in name:
                    self.dynamic_plots[name] = NIPlotting(
                        self.moke.instruments[name], plt=plt)
                else:
                    self.dynamic_plots[name] = NIPlotting(self.moke.instruments[name], plt=plt, plotting_time=300,
                                                          data_per_second=1)

                d = Dock(name, widget=plt, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d)

            elif len(name.split('_')) == 2 and name.split('_')[1] == "composite":
                layout = pg.GraphicsLayoutWidget()
                plt = dict()
                for key in ["difference", "average", "det1", "det2"]:
                    plt[key] = layout.addPlot(title=key)
                    layout.nextRow()
                self.dynamic_plots[name] = WollastonPlotting(
                    self.moke.instruments[name.split('_')[0]], plt=plt)
                d = Dock(name, widget=layout, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d, 'right')

            elif len(name.split('_')) >= 2 and name.split('_')[-1] == "fft":
                layout = pg.GraphicsLayoutWidget()
                inst_name = '_'.join(name.split('_')[:-1])
                plt = dict()
                for key in self.moke.instruments[inst_name].ports.values():
                    plt[key] = layout.addPlot(title=key)
                    layout.nextRow()
                # if the instrument is wollaston, add diff and sum
                if inst_name[:-1] == 'wollaston':
                    for key in ['diff', 'sum']:
                        plt[key] = layout.addPlot(title=key)
                        layout.nextRow()
                self.dynamic_plots[name] = FFTplotting(
                    self.moke.instruments[inst_name], plt=plt)
                d = Dock(name, widget=layout, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d, 'right')

            elif "camera" in name:
                view = pg.GraphicsView()
                view.useOpenGL()
                viewbox = pg.ViewBox()
                viewbox.setAspectLocked(True)
                plt = pg.ImageItem()
                viewbox.addItem(plt)
                view.setCentralItem(viewbox)
                self.dynamic_plots[name] = CameraPlotting(
                    self.moke.instruments[name], plt=plt, view=viewbox)
                d = Dock(name, widget=view, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d, 'right')

            elif name == "3D_fields":
                w = DynamicHPPlot(self.moke.instruments['hallprobe'])
                d = Dock(name, widget=w, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d, 'right')

            elif name == "console":
                w = ConsoleWidget(self.moke)
                d = Dock("console", widget=w, closable=True)
                d.sigClosed.connect(partial(self.dock_closed, name))
                self.dock_dict.update({name: d})
                self.dockarea.addDock(d)

        except KeyError:
            traceback.print_exc()

    def dock_closed(self, name):
        try:
            self.dock_dict.pop(name)
            self.dynamic_plots.pop(name)
        except KeyError:
            pass
        self.sigDockClosed.emit(name)

    def remove_dock(self, name):
        try:
            self.dock_dict[name].close()
        except KeyError:
            print(name, ' not one of the docks')

    def start_timer(self):
        self.timer.start(int(1000.0 / self.framerate))

    def update_plot(self):
        for p in self.dynamic_plots.values():
            p.plot()

    def closeEvent(self, ce):
        self.timer.stop()
        self.close()


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    import gui.exception_handling

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = MokeDocker(moke)
        aw.show()
        qApp.exec_()
