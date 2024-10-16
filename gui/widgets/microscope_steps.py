import sys
import os

import pandas as pd
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import numpy as np
import warnings

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.dockarea import *
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal

from experiments.basic import zero_magnet
from experiments.take_field_steps_hamamatsu import take_steps
import threading


class ApplySteps(QWidget):

    def __init__(self, moke, data_folder=''):
        super().__init__()
        self.setWindowTitle('Kerr microscope - field steps experiment ')
        self.moke = moke
        self.stop_event = threading.Event()
        self.plotting_data = []

        # set the data folder, and make sure it exists
        if not data_folder:
            self.saving_dir = ''
        elif data_folder and not os.path.isdir(data_folder):
            Warning('Given data folder does not exist! Reverting to default')
            self.saving_dir = ''
        else:
            self.saving_dir = data_folder
        params_dict[0]["children"][0]["value"] = self.saving_dir

        self.params = Parameter.create(
            name='params', type='group', children=params_dict)
        self.params.sigTreeStateChanged.connect(self.params_changed)
        self.paramtree = ParameterTree()
        self.paramtree.setParameters(self.params, showTop=False)
        self.dock_area = DockArea()
        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.dock_area)
        self.setLayout(layout)
        self.resize(1200, 700)

        self.plots = [pg.PlotWidget(), pg.PlotWidget()]
        dock0 = Dock('Hysteresis', widget=self.plots[0], closable=False)
        self.dock_area.addDock(dock0)
        dock1 = Dock('Time signal', widget=self.plots[1], closable=False)
        self.dock_area.addDock(dock1)

    def run_experiment(self):
        self.plotting_data = []
        experiment_parameters = self.create_experiment_params_dict()
        signals = self.create_signal_from_parameters()
        self.tune_stop = threading.Event()
        tuning_thread = threading.Thread(target=take_steps,
                                         args=[self.moke, signals, self.tune_stop,
                                               self.saving_dir, self.update_plot_data,
                                               experiment_parameters])
        tuning_thread.daemon = True
        tuning_thread.start()

    def stop_experiment(self):
        try:
            self.tune_stop.set()
        except AttributeError:
            pass
        finally:
            zero_magnet(self.moke)
            print('Zeroed the magnet')

    def closeEvent(self, event):
        # Stop the tuning thread and zero magnets when closing the window
        self.stop_experiment()

    def params_changed(self, param, changes):
        """Function called whenever one of the parameters is changed"""
        for param, change, data in changes:
            # print(param, change, data, param.parent())
            if change == "value":
                if param.name() == 'Saving dir':
                    self.saving_dir = data
                if param.parent().name() == 'Plotting':
                    self.update_plot()
            elif change == "activated":
                if param.name() == "Run":
                    self.run_experiment()
                elif param.name() == "Stop":
                    self.stop_experiment()
                elif param.name() == "Import":
                    self.params.child(
                        "Signal",
                        "Custom signal",
                        "Path").setValue(self.get_filepath())
                    self.params.child(
                        "Signal",
                        "Custom signal",
                        "Use custom signal").setValue(True)

    def create_signal_from_parameters(self):
        if self.params.child("Signal", "Custom signal", "Use custom signal").value():
            path = self.params.child("Signal", "Custom signal", "Path").value()
            print(f'Loading signal from {path}')
            signals = np.loadtxt(path)
            assert signals.shape[1] == 3, 'Wrong signal in CSV file, must have 3 columns'
        else:
            nb_steps = self.params.child("Signal", "Predefined signals", "Number of points per repetition").value()
            signal_types = {'sinus': lambda x: np.sin(x),
                            'triangle': lambda x: 2 / np.pi * np.arcsin(np.sin(x))}
            signal_generator = signal_types[self.params.child("Signal", "Predefined signals", "Signal type").value()]
            amplitudes = [0., 0., 0.]
            amplitudes[0] = self.params.child("Signal", "Predefined signals", "Amplitudes", "X").value()
            amplitudes[1] = self.params.child("Signal", "Predefined signals", "Amplitudes", "Y").value()
            amplitudes[2] = self.params.child("Signal", "Predefined signals", "Amplitudes", "Z").value()
            phases = [0., 0., 0.]
            phases[0] = np.deg2rad(self.params.child("Signal", "Predefined signals", "Phases", "X").value())
            phases[1] = np.deg2rad(self.params.child("Signal", "Predefined signals", "Phases", "Y").value())
            phases[2] = np.deg2rad(self.params.child("Signal", "Predefined signals", "Phases", "Z").value())
            offsets = [0., 0., 0.]
            offsets[0] = self.params.child("Signal", "Predefined signals", "Offsets", "X").value()
            offsets[1] = self.params.child("Signal", "Predefined signals", "Offsets", "Y").value()
            offsets[2] = self.params.child("Signal", "Predefined signals", "Offsets", "Z").value()
            seq = []
            for t in np.linspace(0, 2 * np.pi, nb_steps + 1):
                seq.append([
                    amplitudes[0] * signal_generator(t + phases[0] + offsets[0]),
                    amplitudes[1] * signal_generator(t + phases[1] + offsets[1]),
                    amplitudes[2] * signal_generator(t + phases[2] + offsets[2])
                ])
            seq = seq[:-1]
            signals = np.array(seq)
        return signals

    def create_experiment_params_dict(self):
        expprms = dict()
        expprms['n_loops'] = self.params.child("Running the experiment", "Number of repetitions").value()
        expprms['degauss'] = self.params.child("Running the experiment", "deGauss").value()
        expprms['nb_images_per_step'] = self.params.child("Running the experiment", "Number images per step").value()
        expprms['only_save_average_of_images'] = self.params.child("Running the experiment", "Only save average of images").value()
        expprms['Kp'] = self.params.child("Running the experiment", "PID tuning", "Kp").value()
        expprms['nb_points_used_for_tuning'] = self.params.child("Running the experiment", "PID tuning", "Number points for tuning").value()
        expprms['stop_criterion_tuning_mT'] = self.params.child("Running the experiment", "PID tuning", "Mean error HP stop criterion").value()
        expprms['skip_loops'] = self.params.child("Running the experiment", "Skip loops").value()
        return expprms

    def update_plot_data(self, t, fields, image):
        self.plotting_data.append({
            't': t, 'Bx': fields[0], 'By': fields[1], 'Bz': fields[2],
            'sum camera intensity': np.sum(image)
        })
        self.update_plot()

    def update_plot(self):
        data = pd.DataFrame(self.plotting_data)
        if len(data) == 0:
            return
        selected_field = self.params.child("Plotting", "Field to plot").value()
        nb_steps = self.params.child("Signal", "Predefined signals", "Number of points per repetition").value()
        len_data = len(data['sum camera intensity'])
        remove_linear_drift = self.params.child("Plotting", "Remove global linear drift").value()
        if remove_linear_drift:
            try:
                # take first point of every cycle for linear fit, excluding the first and current cycle
                drift, _ = np.polyfit(range(0, len_data, nb_steps), data['sum camera intensity'][0::nb_steps], 1)
                data['sum camera intensity'] -= drift * range(len_data)
            except:
                pass
        try_faraday_compensation = self.params.child("Plotting", "TODO Try Faraday compensation").value()
        if try_faraday_compensation:
            # TODO currently not implemented
            pass
        data_processing = self.params.child("Plotting", "Data processing").value()
        if data_processing == 'average loops':
            fields = np.zeros(min(nb_steps, len(data)))
            intensities = np.zeros(min(nb_steps, len(data)))
            for i in range(nb_steps):
                intensities[i] = np.mean(data['sum camera intensity'][i::nb_steps])
                fields[i] = np.mean(data[selected_field][i::nb_steps])
        else:
            fields = data[selected_field]
            intensities = data['sum camera intensity']
        self.plots[0].plot(fields, intensities, clear=True, symbol='x')
        self.plots[1].plot(data['t'], data['sum camera intensity'], clear=True, symbol='x')

    def get_filepath(self):
        file_path = QFileDialog.getOpenFileName(
            self, "Select file", "", "CSV (*.csv)")[0]
        print('Imported File: ', file_path)
        if file_path:
            return file_path
        else:
            return ''


params_dict = [
    {
        "name": "Running the experiment",
        "type": "group",
        "children": [
            {"name": "Saving dir", "type": "str", "value": ""},
            {"name": "Run", "type": "action"},
            {"name": "Stop", "type": "action"},
            {"name": "Number of repetitions", "type": "int", "value": 4, "limits": [-1, 10 ** 100]},
            {"name": "deGauss", "type": "bool", "value": True},
            {"name": "Skip loops", "type": "int", "value": 1, "limits": [0, 10 ** 100]},
            {"name": "Number images per step", "type": "int", "value": 10, "limits": [1, 10**100]},
            {"name": "Only save average of images", "type": "bool", "value": True},
            {
                "name": "PID tuning",
                "type": "group",
                "expanded": False,
                "children": [
                    {"name": "Kp", "type": "float", "value": 0.5, "step": 0.1},
                    {"name": "Number points for tuning", "type": "int", "value": 1000},
                    {"name": "Mean error HP stop criterion", "type": "float", "suffix": "mT", "value": 0.05, "step": 0.01},
                ],
            },
        ],
    },
    {
        "name": "Signal",
        "type": "group",
        "children": [
            {
                "name": "Predefined signals",
                "type": "group",
                "children": [
                    {"name": "Number of points per repetition", "type": "int", "value": 50, "limits": [1, 10 ** 100]},
                    {"name": "Signal type", "type": "list", "limits": ["triangle", "sinus"], "value": "triangle"},
                    {
                        "name": "Amplitudes",
                        "type": "group",
                        "children": [
                            {"name": "X", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                            {"name": "Y", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                            {"name": "Z", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                        ],
                    },
                    {
                        "name": "Phases",
                        "type": "group",
                        "expanded": False,
                        "children": [
                            {"name": "X", "type": "float", "value": 0, "suffix": u"\N{DEGREE SIGN}", "step": 0.1},
                            {"name": "Y", "type": "float", "value": 0, "suffix": u"\N{DEGREE SIGN}", "step": 0.1},
                            {"name": "Z", "type": "float", "value": 0, "suffix": u"\N{DEGREE SIGN}", "step": 0.1},
                        ],
                    },
                    {
                        "name": "Offsets",
                        "type": "group",
                        "expanded": False,
                        "children": [
                            {"name": "X", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                            {"name": "Y", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                            {"name": "Z", "type": "float", "value": 0, "suffix": "mT", "step": 0.1},
                        ],
                    },

                ],
            },
            {
                "name": "Custom signal",
                "type": "group",
                "expanded": False,
                "children": [
                    {'name': 'Import', 'type': 'action'},
                    {'name': 'Use custom signal', 'type': 'bool', 'value': False},
                    {'name': 'Path', 'type': 'str', 'value': ''},
                ],
            },
        ],
    },
    {
        "name": "Plotting",
        "type": "group",
        "children": [
            {"name": "Field to plot", "type": "list", "limits": ["Bx", "By", "Bz"], "value": "Bx"},
            {"name": "Data processing", "type": "list", "limits": ["none", "average loops"], "value": "none"},
            {'name': 'Remove global linear drift', 'type': 'bool', 'value': False},
            {'name': 'TODO Try Faraday compensation', 'type': 'bool', 'value': False},
        ],
    }
]


if __name__ == '__main__':
    qApp = QApplication(sys.argv)
    aw = ApplySteps(1)

    aw.show()
    qApp.exec_()
