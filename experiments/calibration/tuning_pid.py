from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph as pg
import threading
import numpy as np
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QApplication, qApp
from PyQt5.QtCore import pyqtSignal, Qt
import time
import os
if __name__ == "__main__":
    import sys
    sys.path.append(os.getcwd())
from gui.widgets.moke_docker import MokeDocker
from experiments.basic import zero_magnet, deGauss
from data.signal_generation import *


COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class PIDtuningWidget(QWidget):
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
        params_list = [{'name': 'Tuning experiment', 'type': 'group', 'children': [
            {'name': 'Kp', 'type': 'float', 'value': 0.0, 'step': 0.1},
            {'name': 'Ki', 'type': 'float', 'value': 0.0, 'step': 0.1},
            {'name': 'Kd', 'type': 'float', 'value': 0.0, 'step': 0.1},
            {'name': 'Field', 'type': 'float', 'value': 10, 'step': 0.1},
            {'name': 'Run', 'type': 'action'}
        ]}
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
        self.result_data = None
        # a few helper attributes
        self.lines = []
        self.set_lines = []
        self.first_run = True
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

    def thread_worker(self, Kp, Ki, Kd, field, stop_event):
        """Thread worker which runs the experiment"""
        moke = self.moke
        magnet = moke.instruments['hexapole']
        hp = moke.instruments['hallprobe']
        # update the pid feedback of the magnet
        magnet.feedback.Kp = Kp
        magnet.feedback.Ki = Ki
        magnet.feedback.Kd = Kd
        magnet.update_feedback()
        # zero the signal
        deGauss(moke)
        print('Zeroing the signal')
        zero_magnet(moke)
        if stop_event.is_set():
            return
        start_time = magnet.get_time()
        zeros_time = 0.5
        time.sleep(zeros_time)
        # field = 20
        i, pole = 0, 'A'
        print('Applying {} mT to pole {}'.format(field, pole))
        constants = np.zeros(3)
        constants[i] = field
        if stop_event.is_set():
            return
        # signal = get_const_signal(constants)
        # signal = [
        #     lambda x: field / 2 * (np.tanh(3 * (x - 1)) + 1),
        #     get_const_fun(0),
        #     get_const_fun(0)
        # ]
        signal = [
            get_sin_fun(field, 1, 0),
            get_const_fun(0),
            get_const_fun(0)
        ]
        signal_duration_time = 5
        start_time += 1
        signal_start_time = magnet.stage_data(signal, signal_duration_time)
        # get the data from the last 3 seconds and plot
        self.result_data = hp.get_data(
            start_time=start_time, end_time=start_time + signal_duration_time)
        self.set_signal = self.result_data.copy()
        self.set_signal.loc[start_time:signal_start_time, :] = 0
        for i, key in enumerate(self.set_signal):
            t = self.set_signal.loc[signal_start_time:, :].index
            t -= t[0]
            self.set_signal.loc[signal_start_time:,
                                key] = signal[i](t)
        # zero the magnet
        zero_magnet(moke)
        # update the plot with the new data
        self.sigUpdatePlot.emit()

    def run_experiment(self):
        if not self.experiment_thread.is_alive():
            # get the parameter values
            Kp = self.params.child('Tuning experiment', 'Kp').value()
            Ki = self.params.child('Tuning experiment', 'Ki').value()
            Kd = self.params.child('Tuning experiment', 'Kd').value()
            field = self.params.child('Tuning experiment', 'Field').value()
            print(Kp, Ki, Kd)
            # start the experiment thread
            self.experiment_thread = threading.Thread(
                target=self.thread_worker, args=[Kp, Ki, Kd, field, self.stop_event])
            self.experiment_thread.daemon = True
            self.stop_event.clear()
            self.experiment_thread.start()

    def stop_experiment(self):
        self.stop_event.set()

    def update_plot(self):
        data = self.result_data
        if data is not None:
            data_filtered = filter_data(data)
            clear = True
            if self.first_run:
                self.result_plot.setLabel('bottom', 't [s]')
                self.result_plot.setLabel('left', 'B [mT]')
                self.result_plot.showGrid(y=True)
            for i, key in enumerate(data):
                if self.first_run:
                    self.lines.append(self.result_plot.plot(
                        data_filtered.index, data_filtered[key].values, clear=clear, pen=PENS[i], name=key))
                    self.set_lines.append(self.result_plot.plot(
                        self.set_signal.index, self.set_signal[key].values, pen=pg.mkPen(COLORS[i], style=Qt.DotLine, width=2), name=key + ' set'))
                    clear = False
                else:
                    self.lines[i].setData(
                        data_filtered.index, data_filtered[key].values)
                    self.set_lines[i].setData(
                        self.set_signal.index, self.set_signal[key].values)
            self.first_run = False

    def closeEvent(self, ce):
        self.stop_event.set()
        if self.experiment_thread.is_alive():
            self.experiment_thread.join()
        self.close()


def filter_data(data):
    return data


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    # import gui.exception_handling

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = PIDtuningWidget(moke)
        aw.show()
        qApp.exec_()
