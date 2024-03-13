from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph as pg
import threading
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QApplication, qApp
from PyQt5.QtCore import pyqtSignal, Qt
import time
import os
if __name__ == "__main__":
    import sys
    sys.path.append(os.getcwd())
from gui.widgets.moke_docker import MokeDocker
from experiments.basic import zero_magnet, deGauss
from data.signal_generation import get_sin_fun, get_const_fun
from data.signal_processing import filter_signal_pd as filter_data
from experiments.basic import magnet_loop_tuning


COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class LoopTuningWidget(QWidget):
    sigUpdatePlot = pyqtSignal()

    def __init__(self, moke, data_folder=''):
        self.moke = moke
        QWidget.__init__(self)

        # add the moke docker
        dock_list = [
            "hallprobe",
            "hexapole",
            "temperature"
        ]
        self.moke_docker = MokeDocker(moke, dock_list=dock_list)

        # create the parameters
        params_list = [
            {'name': 'Kp', 'type': 'float', 'value': 0.4, 'step': 0.1},
            {'name': 'Ki', 'type': 'float', 'value': 0.3, 'step': 0.1},
            {'name': 'Kd', 'type': 'float', 'value': 1, 'step': 0.1},
            {'name': 'Field', 'type': 'float', 'value': 10, 'step': 0.1},
            {'name': 'Period', 'type': 'float', 'value': 1, 'step': 0.1},
            {'name': 'Run', 'type': 'action'},
            {'name': 'Stop', 'type': 'action'}
        ]
        self.params = Parameter.create(
            name='params', type='group', children=params_list)
        self.params.sigTreeStateChanged.connect(self.params_changed)
        # add the parameter tree for editing the parameters
        self.paramtree = ParameterTree()
        self.paramtree.setParameters(self.params, showTop=False)
        self.paramtree.setMinimumWidth(250)
        self.paramtree.setMaximumWidth(500)

        # create the result plot and data
        self.result_plot = pg.PlotWidget(title='Result')
        self.result_plot.addLegend()
        # a few helper attributes
        self.lines = []
        self.set_lines = []
        self.first_run = True
        self.set_signal = None
        # get the data from the last period and plot
        self.result_data = None
        self.set_signal = None

        # set the layout
        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.moke_docker)
        layout.addWidget(self.result_plot)

        self.setLayout(layout)
        self.resize(1100, 500)
        # create the exoeriment thread variable
        self.experiment_thread = threading.Thread()
        self.stop_event = threading.Event()

        # connect to the signal for updating the plot
        self.sigUpdatePlot.connect(self.update_plot)

    def params_changed(self, param, changes):
        """Function called whenever one of the parameters is changed"""
        for param, change, data in changes:
            if change == "activated":
                if param.name() == "Run":
                    # run the experiment
                    self.run_experiment()
                if param.name() == "Stop":
                    # run the experiment
                    self.stop_event.set()

    def thread_worker(self, Kp, Ki, Kd, field, period, stop_event):
        """Thread worker which runs the experiment"""
        try:
            moke = self.moke
            magnet = moke.instruments['hexapole']
            hp = moke.instruments['hallprobe']
            # zero the signal
            # deGauss(moke)
            print('Zeroing the signal')
            # zero_magnet(moke)
            if stop_event.is_set():
                return
            zeros_time = 0.5
            time.sleep(zeros_time)
            # field = 20
            if stop_event.is_set():
                return
            signal = [
                get_sin_fun(field, period, 0),
                # lambda t: field * np.logical_and(
                #     t > period / 4, t < period * 3 / 4).astype(float),
                get_const_fun(0),
                get_const_fun(0)
            ]
            # define the parameters
            parameters = {
                "Kp": Kp,
                "Ki": Ki,
                "Kd": Kd,
            }
            signal_start_time = magnet.stage_data(signal, period)
            # start tuning thread
            tune_start = signal_start_time + 2 * period
            tuning_thread = threading.Thread(target=magnet_loop_tuning,
                                             args=(moke, signal, period,
                                                   tune_start, stop_event,
                                                   parameters))
            tuning_thread.daemon = True
            tuning_thread.start()

            # wait for two periods
            magnet.wait_for_time(signal_start_time + 2 * period, stop_event)
            if stop_event.is_set():
                zero_magnet(moke)
                return
            # start collecting the tuning data
            tune_start = signal_start_time + 2 * period
            while True:
                if magnet.get_time() >= tune_start + period:
                    print(
                        'Warning! Experiment not keeping up with the data acquisition')
                magnet.wait_for_time(tune_start + period, stop_event)
                if stop_event.is_set():
                    break
                # get the wanted and measured data from the last period
                signal_measured = filter_data(hp.get_data(start_time=tune_start,
                                                          end_time=tune_start + period, wait=True))
                t = signal_measured.index
                t -= t[0]
                values = np.vstack([f(t) for f in signal]).T
                signal_wanted = pd.DataFrame(values,
                                             columns=signal_measured.columns, index=t)
                signal_measured.index = t

                tune_start += 2 * period

                # get the data from the last period and plot
                self.result_data = signal_measured
                self.set_signal = signal_wanted
                print('Max error: ', np.max(
                    np.abs(self.result_data.values - self.set_signal.values)), ' mT')
                # update the plot with the new data
                self.sigUpdatePlot.emit()
        finally:
            tuning_thread.join()
            # zero the magnet
            zero_magnet(moke)

    def run_experiment(self):
        if not self.experiment_thread.is_alive():
            # get the parameter values
            Kp = self.params.child('Kp').value()
            Ki = self.params.child('Ki').value()
            Kd = self.params.child('Kd').value()
            field = self.params.child('Field').value()
            period = self.params.child('Period').value()
            print(Kp, Ki, Kd)
            # start the experiment thread
            self.experiment_thread = threading.Thread(
                target=self.thread_worker, args=[Kp, Ki, Kd, field, period, self.stop_event])
            self.experiment_thread.daemon = True
            self.stop_event.clear()
            self.experiment_thread.start()

    def stop_experiment(self):
        self.stop_event.set()

    def update_plot(self):
        data = self.result_data
        if data is not None:
            clear = True
            if self.first_run:
                self.result_plot.setLabel('bottom', 't [s]')
                self.result_plot.setLabel('left', 'B [mT]')
                self.result_plot.showGrid(y=True)
            for i, key in enumerate(data):
                if self.first_run:
                    self.lines.append(self.result_plot.plot(
                        data.index, data[key].values, clear=clear, pen=PENS[i], name=key))
                    self.set_lines.append(self.result_plot.plot(
                        self.set_signal.index, self.set_signal[key].values, pen=pg.mkPen(COLORS[i], style=Qt.DotLine,
                                                                                         width=2), name=key + ' set'))
                    clear = False
                else:
                    self.lines[i].setData(data.index, data[key].values)
                    self.set_lines[i].setData(
                        self.set_signal.index, self.set_signal[key].values)
            self.first_run = False

    def closeEvent(self, ce):
        self.stop_event.set()
        if self.experiment_thread.is_alive():
            self.experiment_thread.join()
        self.close()


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    # import gui.exception_handling

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = LoopTuningWidget(moke)
        aw.show()
        qApp.exec_()
