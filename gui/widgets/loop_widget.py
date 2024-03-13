from functools import partial
import traceback
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.dockarea import *
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
import threading
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import *
import time
import os
import sys
from inspect import getmembers, isfunction
if __name__ == "__main__":
    sys.path.append(os.getcwd())

from experiments.take_loop import take_sin_loop, take_loop
from data.live_processing import get_binned_data
from experiments.basic import temp_too_high_stop
import experiments.custom_loop as custom

COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class LoopWidget(QWidget):
    sigUpdatePlot = pyqtSignal()

    def __init__(self, moke, data_folder=''):
        self.moke = moke
        QWidget.__init__(self)
        # set the data folder, and make sure it exists
        if data_folder is None:
            self.saving_dir = ''
        elif data_folder != '' and not os.path.isdir(data_folder):
            Warning('Given data folder does not exist! Reverting to default')
            self.saving_dir = ''
        else:
            self.saving_dir = data_folder

        # set the number of bins for plotting
        self.plotting_bins = 1000
        # number of data points in each bin
        self.n_data = np.zeros(self.plotting_bins)

        self.stop_event = threading.Event()
        self.plotting_variables_mapping = {
            't': 't', 'hallprobe_A': 'Bx', 'hallprobe_B': 'By', 'hallprobe_C': 'Bz',
            'diff1': 'Wollaston 1 diff', 'sum1': 'Wollaston 1 sum', 'ratio1': 'Wollaston 1 ratio',
            'woll1det1': 'Wollaston 1 det1', 'woll1det2': 'Wollaston 1 det2',
            'diff2': 'Wollaston 2 diff', 'sum2': 'Wollaston 2 sum', 'ratio2': 'Wollaston 2 ratio',
            'woll2det1': 'Wollaston 2 det1', 'woll2det2': 'Wollaston 2 det2'}
        # create the dataframe for plotting
        self.plotting_data = pd.DataFrame(columns=list(
            self.plotting_variables_mapping.values()))
        # create the lock for accessing it
        self.plotting_data_lock = threading.Lock()

        # create the parameters and parameter tree
        self.plotting_parameters = PlottingParameters(name="Plotting")
        self.experiment_parameters_entries = ExperimentParams(
            name='Experiment Parameters')
        params_list = [self.experiment_parameters_entries,
                       {'name': 'Running the experiment', 'type': 'group', 'children': [
                           {'name': 'Saving dir', 'type': 'str',
                               'value': self.saving_dir},
                           {'name': 'Run', 'type': 'action'},
                           {'name': 'Stop', 'type': 'action'}
                       ]},
                       self.plotting_parameters,
                       {'name': 'Running Custom Experiment', 'type': 'group', 'children': [
                           {'name': 'Experiment name', 'type': 'list',
                               'values': self.get_custom_experiment_list().keys()},
                           {'name': 'File name', 'type': 'str', 'value': ''},
                           {'name': 'Run custom', 'type': 'action'},
                           {'name': 'Stop', 'type': 'action'}
                       ]}
                       ]
        self.params = Parameter.create(
            name='params', type='group', children=params_list)
        self.params.sigTreeStateChanged.connect(self.params_changed)
        # add the parameter tree for editing the parameters
        self.paramtree = ParameterTree()
        self.paramtree.setParameters(self.params, showTop=False)
        self.paramtree.setMinimumWidth(500)
        self.paramtree.setMaximumWidth(600)

        # create the dock area
        self.dock_area = DockArea()
        self.plotting_parameters.sigNewPlotAdded.connect(self.add_new_plot)
        self.plots = dict()  # variable keeping track of all the plots
        self.docks = dict()  # variable keeping track of all the docks
        self.dock_area.setMinimumWidth(600)
        # by default add plots for both wollastones
        self.plotting_parameters.addNew('Wollaston 1')
        self.plotting_parameters.addNew('Wollaston 2')

        # set the layout
        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.dock_area)

        self.setLayout(layout)
        self.resize(1200, 500)
        # connect to the signal for updating the plot
        self.sigUpdatePlot.connect(self.update_plot)
        # connect the signal for updating the plotting parameters
        self.plotting_parameters.sigParametersChanged.connect(self.update_plot)
        # create the exoeriment thread variable
        self.experiment_thread = threading.Thread()

        # thread for processing the data
        self.calculate_data_thread = None

    def add_new_plot(self, name, params):
        """Docks a new plot"""
        self.plots[name] = pg.PlotWidget(title=params['title'])
        d = Dock(name, widget=self.plots[name], closable=True)
        d.sigClosed.connect(partial(self.plotting_parameters.removePlot, name))
        d.sigClosed.connect(partial(self.dock_closed, name))
        self.dock_area.addDock(d, position='bottom')
        self.docks[name] = d
        self.update_plot()

    def dock_closed(self, name):
        """Closes the docks and removes it internally"""
        self.plots.pop(name)
        self.docks.pop(name)

    def params_changed(self, param, changes):
        """Function called whenever one of the parameters is changed"""
        for param, change, data in changes:
            if change == "value":
                path = self.params.childPath(param)
                if path[0] == 'Experiment Parameters' and param.name() == "Use custom signal" and param.value():
                    if self.experiment_parameters_entries.custom_signal_path.value() == '':
                        self.experiment_parameters_entries.custom_signal_path.setValue(
                            self.get_filepath())
                elif path[0] == 'Plotting':
                    self.plotting_parameters.params_changed(path, data)
                    self.update_plot()
                elif path[-1] == 'Saving dir':
                    self.saving_dir = data
            elif change == "activated":
                if param.name() == "Run":
                    self.run_experiment()
                if param.name() == "Run custom":
                    self.run_custom_experiment()
                elif param.name() == "Stop":
                    self.stop_experiment()
                elif param.name() == "Import":
                    self.experiment_parameters_entries.custom_signal_path.setValue(
                        self.get_filepath())
                    self.experiment_parameters_entries.custom_signal_tickbox.setValue(
                        True)

    def get_experiment_parameters(self):
        """Updates the internal dictionary of experimental parameters depending on the GUI values"""
        experiment_parameters = dict()
        # define the common experiment parameters
        experiment_parameters['skip_loops'] = self.params.child(
            'Experiment Parameters', 'Skip loops').value()
        experiment_parameters['save'] = self.params.child(
            'Experiment Parameters', 'Save').value()
        experiment_parameters['degauss'] = self.params.child(
            'Experiment Parameters', 'deGauss').value()
        experiment_parameters['n_loops'] = self.params.child(
            'Experiment Parameters', 'Number of loops').value()
        experiment_parameters['tune_loop'] = self.params.child(
            'Experiment Parameters', 'Tune loop').value()
        experiment_parameters['saving_loc'] = self.params.child(
            'Running the experiment', 'Saving dir').value()

        # check if custom or sin signal
        if self.experiment_parameters_entries.custom_signal_tickbox.value():
            # initialise signal, but allow it to be set later based on the files in the folder
            experiment_parameters['signal'] = None
        else:
            for key in ['amplitudes', 'phases', 'offsets']:
                experiment_parameters[key] = [
                    self.experiment_parameters_entries.sin_field_entries[key][d].value() for d in ['X', 'Y', 'Z']]

            experiment_parameters['frequency'] = self.experiment_parameters_entries.sin_field_entries[
                'frequency'].value()

        return experiment_parameters

    def loop_worker(self):
        """Thread worker which runs the experiment"""
        try:
            # get the experiment parameters
            experiment_parameters = self.get_experiment_parameters()
            # if something wrong return
            if not experiment_parameters:
                return

            if os.path.isdir(experiment_parameters['saving_loc']):
                filename = 'LoopTaking_' + \
                    time.strftime("%Y%m%d-%H%M%S") + '.h5'
                experiment_parameters['saving_loc'] = os.path.join(
                    self.saving_dir, filename)
            # run the experiment
            print('Running the experiment...')

            if not self.experiment_parameters_entries.custom_signal_tickbox.value():
                print('Taking sin loop.')
                take_sin_loop(self.moke, stop_event=self.stop_event,
                              data_callback=self.update_plot_data, **experiment_parameters)
            else:
                # get the directory
                signal_file = self.experiment_parameters_entries.custom_signal_path.value()
                # check if dir valid. If not, try prompting for another
                print('Running custom signal')
                signal = np.loadtxt(signal_file)
                assert signal.shape[1] == 4, 'Wrong signal in CSV file'
                # make sure to drop all plotting data
                self.plotting_data_lock.acquire()
                self.plotting_data = self.plotting_data.iloc[0:0]
                self.plotting_data_lock.release()
                print('gui signal: ', signal)
                experiment_parameters['signal'] = signal
                # check if temperature is too high
                temp_too_high_stop(self.moke)
                # start taking loop
                take_loop(self.moke, stop_event=self.stop_event,
                          data_callback=self.update_plot_data, **experiment_parameters)
        except:
            traceback.print_exc()

    def run_experiment(self):
        if not self.experiment_thread.is_alive():
            self.clear_data()
            # start the experiment thread
            self.experiment_thread = threading.Thread(target=self.loop_worker)
            self.experiment_thread.daemon = True
            self.stop_event.clear()
            self.experiment_thread.start()
        else:
            print('Experiment thread running, first stop the current experiment!')

    def clear_data(self):
        """Clears the plotting data"""
        # drop all data
        self.plotting_data_lock.acquire()
        self.plotting_data = self.plotting_data.iloc[0:0]
        self.plotting_data_lock.release()

    def stop_experiment(self):
        self.stop_event.set()

    def get_filepath(self):
        file_path = QFileDialog.getOpenFileName(
            self, "Select file", "", "CSV (*.csv)")[0]
        print('Imported File: ', file_path)
        if file_path:
            return file_path
        else:
            return ''

    def calculate_data(self, inst_data, n_periods=1, data_per_period=1000):
        try:
            self.plotting_data_lock.acquire()
            # get the binned data
            data_binned = get_binned_data(
                inst_data, n_periods=n_periods, data_per_period=data_per_period)
            data_binned.rename(
                columns=self.plotting_variables_mapping, inplace=True)
            # generate the bins
            if self.plotting_data.shape[0] == 0 or not self.plotting_parameters.averaging:
                self.plotting_data = data_binned
                self.n_data = np.ones(self.plotting_data.shape[0])
            # else bin the new data over the existing bins and then average
            else:
                # if averaging, combine with the previous data, but need to be careful of nan values
                fltr = data_binned["t"].notnull().values
                self.plotting_data.iloc[fltr] = self.plotting_data.iloc[fltr].multiply(
                    self.n_data[fltr], axis=0) + data_binned.iloc[fltr]
                self.n_data[fltr] += 1
                self.plotting_data.iloc[fltr] = self.plotting_data.iloc[fltr].divide(
                    self.n_data[fltr], axis=0)
        finally:
            self.plotting_data_lock.release()

        # update the plot
        self.sigUpdatePlot.emit()

    def update_plot_data(self, inst_data, n_periods=1, data_per_period=1000):
        if self.calculate_data_thread is not None:
            if not self.calculate_data_thread.is_alive():
                self.calculate_data_thread = threading.Thread(target=self.calculate_data,
                                                              args=(inst_data, n_periods, data_per_period))
                self.calculate_data_thread.daemon = True
                self.calculate_data_thread.start()
        else:
            self.calculate_data_thread = threading.Thread(target=self.calculate_data,
                                                          args=(inst_data, n_periods, data_per_period))
            self.calculate_data_thread.daemon = True
            self.calculate_data_thread.start()

    def update_plot(self):
        try:
            self.plotting_data_lock.acquire()
            for name, p in self.plots.items():
                params = self.plotting_parameters.plots[name]
                p.setLabel('bottom', params['x'])
                p.setLabel('left', params['y'])
                p.plot(np.array(self.plotting_data[params['x']]),
                       np.array(self.plotting_data[params['y']]), clear=True, pen=PENS[0])
            self.plotting_data_lock.release()
        except:
            traceback.print_exc()

    def get_custom_experiment_list(self):
        custom.deep_reload(custom)
        custom_experiments = {
            a[0][:-1]: a[1] for a in getmembers(custom, isfunction) if a[0][-1] == '_'}
        return custom_experiments

    def run_custom_experiment(self):
        custom_experiments = self.get_custom_experiment_list()
        # get the chosen experiment
        chosen_experiment = self.params.child(
            'Running Custom Experiment', 'Experiment name').value()
        # TODO: this doesn't work at the moment, but I could probably make it work in the future
        # check if the chosen one is refresh list, then refresh the list as well
        if chosen_experiment == 'refresh_list':
            self.params.child(
                'Running Custom Experiment', 'Experiment name').setOpts(items=self.get_custom_experiment_list().keys())

        if not self.experiment_thread.is_alive():
            self.experiment_thread = threading.Thread(target=custom_experiments[chosen_experiment],
                                                      args=(self.moke,), kwargs={'loop_widget': self})
            self.experiment_thread.daemon = True
            self.stop_event.clear()
            self.experiment_thread.start()
        else:
            print('Experiment thread running, first stop the current experiment!')

    def closeEvent(self, ce):
        self.stop_event.set()
        if self.experiment_thread.is_alive():
            self.experiment_thread.join()
        self.close()


# duration and speed parameters which are mutually dependent
class ExperimentParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pTypes.GroupParameter.__init__(self, **opts)

        self.addChild({'name': 'Number of loops',
                       'type': 'int', 'value': -1, 'step': 1})
        self.addChild(
            {'name': 'Skip loops', 'type': 'float', 'value': 1, 'step': 1})
        self.addChild(
            {'name': 'Save', 'type': 'bool', 'value': True})
        self.addChild(
            {'name': 'deGauss', 'type': 'bool', 'value': True})
        self.addChild(
            {'name': 'Tune loop', 'type': 'bool', 'value': True})

        self.signal_group = self.addChild({'name': 'Signal', 'type': 'group'})

        # group controlling the sin signal entries
        self.sin_group = self.signal_group.addChild(
            {'name': 'Sin signal', 'type': 'group'})
        self.amp_group = self.sin_group.addChild(
            {'name': 'Amplitudes', 'type': 'group'})
        self.sin_field_entries = dict()

        # Amplitudes
        self.sin_field_entries['amplitudes'] = dict()
        self.sin_field_entries['amplitudes']['X'] = self.amp_group.addChild(
            {'name': 'X', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.sin_field_entries['amplitudes']['Y'] = self.amp_group.addChild(
            {'name': 'Y', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.sin_field_entries['amplitudes']['Z'] = self.amp_group.addChild(
            {'name': 'Z', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.phase_group = self.sin_group.addChild(
            {'name': 'Phases', 'type': 'group', 'expanded': False})

        # Phases
        self.sin_field_entries['phases'] = dict()
        self.sin_field_entries['phases']['X'] = self.phase_group.addChild(
            {'name': 'X', 'type': 'float', 'value': 0, 'suffix': u'\N{DEGREE SIGN}', 'step': 1})
        self.sin_field_entries['phases']['Y'] = self.phase_group.addChild(
            {'name': 'Y', 'type': 'float', 'value': 0, 'suffix': u'\N{DEGREE SIGN}', 'step': 1})
        self.sin_field_entries['phases']['Z'] = self.phase_group.addChild(
            {'name': 'Z', 'type': 'float', 'value': 0, 'suffix': u'\N{DEGREE SIGN}', 'step': 1})
        self.offsets_group = self.sin_group.addChild(
            {'name': 'Offsets', 'type': 'group', 'expanded': False})

        # Offsets
        self.sin_field_entries['offsets'] = dict()
        self.sin_field_entries['offsets']['X'] = self.offsets_group.addChild(
            {'name': 'X', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.sin_field_entries['offsets']['Y'] = self.offsets_group.addChild(
            {'name': 'Y', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.sin_field_entries['offsets']['Z'] = self.offsets_group.addChild(
            {'name': 'Z', 'type': 'float', 'value': 0, 'suffix': 'mT', 'step': 0.1})
        self.sin_field_entries['frequency'] = self.sin_group.addChild({'name': 'Frequency', 'type': 'float',
                                                                       'value': 1, 'suffix': 'Hz', 'step': 0.1})
        self.sin_field_entries['period'] = self.sin_group.addChild({'name': 'Period', 'type': 'float',
                                                                    'value': 1, 'suffix': 's', 'step': 0.1})

        self.sin_field_entries['frequency'].sigValueChanged.connect(
            self.frequencyChanged)
        self.sin_field_entries['period'].sigValueChanged.connect(
            self.periodChanged)

        # add the group for custom signal
        self.custom_signal_group = self.signal_group.addChild(
            {'name': 'Custom signal', 'type': 'group', 'expanded': False})
        self.custom_signal_import = self.custom_signal_group.addChild(
            {'name': 'Import', 'type': 'action'})
        self.custom_signal_tickbox = self.custom_signal_group.addChild(
            {'name': 'Use custom signal', 'type': 'bool', 'value': False})
        self.custom_signal_path = self.custom_signal_group.addChild(
            {'name': 'Path', 'type': 'str', 'value': ''})

        # initialise dependent variables
        self.frequencyChanged()

    def frequencyChanged(self):
        self.sin_field_entries['period'].setValue(1 / self.sin_field_entries['frequency'].value(),
                                                  blockSignal=self.periodChanged)

    def periodChanged(self):
        self.sin_field_entries['frequency'].setValue(1 / self.sin_field_entries['period'].value(),
                                                     blockSignal=self.frequencyChanged)


# plotting group for adding and removing plots
class PlottingParameters(pTypes.GroupParameter):
    sigParametersChanged = pyqtSignal()
    sigNewPlotAdded = pyqtSignal(str, dict)

    def __init__(self, **opts):
        # create as group with plots as subgroups
        opts['type'] = 'group'
        opts['addText'] = "Add"
        opts['addList'] = ['Wollaston 1', 'Wollaston 2']
        pTypes.GroupParameter.__init__(self, **opts)
        # start counting the name of the plots in subgroups
        if 'children' in opts:
            self.plot_number = len(opts['children'])
        else:
            self.plot_number = 0
        self.addChild({'name': 'Averaging', 'type': 'list', 'values': [
            'Cumulative', 'Single shot'], 'value': 'Cumulative'})
        # add a variable keeping track of the plots
        self.plots = dict()
        self.averaging = True

    def addNew(self, instrument):
        available_plotting_variables = ['t', 'Bx', 'By', 'Bz',
                                        instrument + ' diff',
                                        instrument + ' sum',
                                        instrument + ' ratio',
                                        instrument + ' det1',
                                        instrument + ' det2']
        defaults = {'title': instrument, 'x': 'Bx', 'y': instrument + ' ratio'}

        self.plot_number += 1
        name = "Plot " + str(self.plot_number)

        # add the entry
        self.addChild(dict(name=name, type='group',
                           children=[
                               {'name': 'x', 'type': 'list', 'values': available_plotting_variables,
                                'value': defaults['x']},

                               {'name': 'y', 'type': 'list', 'values': available_plotting_variables,
                                'value': defaults['y']}, ]
                           ))

        # remember in the plots in more convenient format
        self.plots[name] = defaults
        # send a signal to update plots in the main gui
        self.sigNewPlotAdded.emit(name, defaults)

    def removePlot(self, name):
        self.removeChild(self.child(name))
        self.plots.pop(name)

    def params_changed(self, path, data):
        if path[1] == 'Averaging':
            if data == 'Cumulative':
                self.averaging = True
            else:
                self.averaging = False
        else:
            self.plots[path[1]][path[2]] = data
            self.sigParametersChanged.emit()


if __name__ == '__main__':
    # import sys
    # from control.instruments.moke import Moke
    # import gui.exception_handling

    app = QApplication(sys.argv)
    aw = LoopWidget(0)
    aw.show()
    qApp.exec_()

    # with Moke() as moke:
    #     app = QApplication(sys.argv)
    #     aw = LoopWidget(moke)
    #     aw.show()
    # qApp.exec_()
