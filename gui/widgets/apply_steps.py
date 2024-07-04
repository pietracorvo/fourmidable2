import sys
import os
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
from experiments.take_field_steps import take_steps
import threading


class ApplySteps(QWidget):
    #sigUpdatePlot = pyqtSignal()

    def __init__(self, moke, data_folder=''):
        super().__init__()
        self.setWindowTitle('Apply field steps experiment ')
        self.moke = moke

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
        self.paramtree.setMinimumWidth(500)
        self.paramtree.setMaximumWidth(600)
        self.dock_area = DockArea()
        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.dock_area)
        self.setLayout(layout)
        self.resize(1200, 500)

    def run_experiment(self):
        experiment_parameters = self.create_experiment_params_dict()
        signals = self.create_signal_from_parameters()
        self.tune_stop = threading.Event()
        take_steps(self.moke, signals, self.tune_stop, self.saving_dir,
                   experiment_parameters)

    def stop_experiment(self):
        try:
            self.tune_stop.set()
        except AttributeError:
            pass
        finally:
            zero_magnet(self.moke)
            print('Zeroed the magnet')

    def params_changed(self, param, changes):
        """Function called whenever one of the parameters is changed"""
        for param, change, data in changes:
            #print(param, change, data)
            if change == "value":
                if param.name() == 'Saving dir':
                    self.saving_dir = data
            #     path = self.params.childPath(param)
            #     if path[0] == 'Experiment Parameters' and param.name() == "Use custom signal" and param.value():
            #         if self.experiment_parameters_entries.custom_signal_path.value() == '':
            #             self.experiment_parameters_entries.custom_signal_path.setValue(
            #                 self.get_filepath())
            #     elif path[0] == 'Plotting':
            #         self.plotting_parameters.params_changed(path, data)
            #         self.update_plot()
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
            path = self.params.child( "Signal", "Custom signal", "Path").value()
            print(f'Loading signal from {path}')
            signals = np.loadtxt(path)
            assert signals.shape[1] == 3, 'Wrong signal in CSV file, must have 3 columns'
        else:
            nb_cycles = self.params.child("Signal", "Predefined signals", "Number of repetitions").value()
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
            seq *= nb_cycles
            signals = np.array(seq)
        return signals

    def create_experiment_params_dict(self):
        expprms = dict()
        expprms['nb_images_per_step'] = self.params.child("Running the experiment", "Number images per step").value()
        expprms['only_save_average_of_images'] = self.params.child("Running the experiment", "Only save average of images").value()
        expprms['Kp'] = self.params.child("Running the experiment", "PID tuning", "Kp").value()
        expprms['nb_points_used_for_tuning'] = self.params.child("Running the experiment", "PID tuning", "Number points for tuning").value()
        expprms['stop_criterion_tuning_mT'] = self.params.child("Running the experiment", "PID tuning", "Mean error HP stop criterion").value()
        return expprms

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
                    {"name": "Number of repetitions", "type": "int", "value": 2, "limits": [1, 10 ** 100]},
                    {"name": "Number of points per repetition", "type": "int", "value": 60, "limits": [1, 10 ** 100]},
                    {"name": "Signal type", "type": "list", "limits": ["sinus", "triangle"], "value": "sinus"},
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
]



if __name__ == '__main__':
    qApp = QApplication(sys.argv)
    aw = ApplySteps(1)

    aw.show()
    qApp.exec_()
