import numpy as np
import pandas as pd
from PyQt5.QtWidgets import *
import threading

from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import traceback
import copy

if __name__ == '__main__':
    import os
    import sys
    sys.path.append(os.getcwd())
from experiments.field_map_unidirectional import field_map_unidirectional


COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class FindCentre(QWidget):
    sigUpdatePlot = pyqtSignal()

    def __init__(self, moke):
        self.moke = moke
        QWidget.__init__(self)

        self.experiment_parameters = {
            "start": -0.02e-3,
            "end": 0.02e-3,
            "direction": "x",
            "save": False
        }
        # the last ran direction. This is to avoid user switching the direction parameter and then wanting to move in the direction which is displayed on the graph
        self.direction_stored = self.experiment_parameters['direction']
        self.stop_event = threading.Event()
        self.plotting_data = pd.DataFrame(
            columns=["x", "y"])

        params_list = [
            {'name': 'Set parameters', 'type': 'group', 'children': [
                {'name': 'Start', 'type': 'float',
                 'value': self.experiment_parameters["start"],
                    'suffix': 'm', 'siPrefix': True,
                    "tip": "Start position relative to the current position"},

                {'name': 'End', 'type': 'float',
                 'value': self.experiment_parameters["end"],
                    'suffix': 'm', 'siPrefix': True,
                    "tip": "End position relative to the current position"},

                {'name': 'Direction', 'type': 'list',
                    'values': ["x", "y", "z"], 'value': self.experiment_parameters['direction'],
                    'tip': "Scan direction"},

                {'name': 'Save', 'type': 'bool',
                 'value': self.experiment_parameters['save'],
                 'tip': "Should the experiment data be saved to a file"},
            ]},
            {'name': 'Running the experiment', 'type': 'group', 'children': [
                {'name': 'Run', 'type': 'action'},
                {'name': 'Stop', 'type': 'action'},
            ]},
            {'name': 'Moving the stage', 'type': 'group', 'children': [
                {'name': 'Find Minimum', 'type': 'action'},
                {'name': 'Move', 'type': 'action'},
            ]}
        ]

        # Create tree of Parameter objects
        self.params = Parameter.create(
            name='params', type='group', children=params_list)
        self.params.sigTreeStateChanged.connect(self.params_changed)

        # add the parameter tree for editing the parameters
        self.paramtree = ParameterTree()
        self.paramtree.setParameters(self.params, showTop=False)
        self.paramtree.setMaximumWidth(250)

        # create the graphics widget
        self.graphics_widget = pg.GraphicsLayoutWidget()
        # add the label signifying the position of the crosshair
        self.label = pg.LabelItem(justify='right')
        self.graphics_widget.addItem(self.label, 0, 0, 1, 1)
        # add the plot and vertical line
        self.plt = self.graphics_widget.addPlot(row=1, col=0)
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.plt.addItem(self.vLine, ignoreBounds=True)
        self.lock_crosshair = False
        self.graphics_widget.setMinimumWidth(600)
        self.set_label()
        # add mouse movement
        self.graphics_widget.scene().sigMouseMoved.connect(self.mouse_moved)
        self.graphics_widget.scene().sigMouseClicked.connect(self.mouse_clicked)

        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.graphics_widget)

        self.setLayout(layout)
        self.resize(1100, 500)

        # update the plot
        self.update_plot()
        # connect to the signal for updating the plot
        self.sigUpdatePlot.connect(self.update_plot)
        # create experiment thread
        self.experiment_thread = threading.Thread()
        self.params.childs[0].opts['readonly'] = False

    def params_changed(self, param, changes):
        # change the experiment parameters depending on user input
        for param, change, data in changes:
            if change == "value":
                name = param.name()
                self.experiment_parameters[name.lower()] = data
            elif change == "activated":
                # only allow stopping while running the experiment
                if self.experiment_thread.is_alive() and param.name() != "Stop":
                    return
                if param.name() == "Run":
                    self.run_experiment()
                elif param.name() == "Stop":
                    self.stop_experiment()
                elif param.name() == "Find Minimum":
                    self.find_lowest()
                elif param.name() == "Move":
                    self.move_to_pos()

    def field_map_worker(self):
        # make sure to disable all of the controls while the experiment is running
        # run the experiment
        print('Running the experiment...')
        testing_range = np.array([self.experiment_parameters["start"],
                                  self.experiment_parameters["end"]]) * 1e6
        direction = copy.deepcopy(self.experiment_parameters["direction"])
        save_data = copy.deepcopy(self.experiment_parameters["save"])
        # record the last direction that we ran (in case the user changes the direction, but then still wants to move in the direction displayed on the graph)
        self.direction_stored = direction
        magnet_signal = [2, 2, 2]
        # if direction=="y":
        #     magnet_signal[0] *= -1
        print(testing_range)
        field_map_unidirectional(self.moke, testing_range, direction, step=100, stop_event=self.stop_event,
                                 data_callback=self.update_plot_data, save_data=save_data, magnet_signal=magnet_signal)

    def run_experiment(self):
        self.plotting_data.drop(self.plotting_data.index, inplace=True)

        self.experiment_thread = threading.Thread(target=self.field_map_worker)
        self.experiment_thread.daemon = True
        self.stop_event.clear()
        self.experiment_thread.start()

    def find_lowest(self):
        # finds the lowest point in the plotting data and marks it
        data = self.plotting_data
        if data.shape[0] != 0:
            # fit a quadratic to the data
            coeff = np.polyfit(
                self.plotting_data["x"], self.plotting_data["y"], 2)

            def fit_fn(x): return coeff[0] * x**2 + coeff[1] * x + coeff[2]
            # add the fit to the graph
            self.plt.plot(self.plotting_data["x"], fit_fn(
                self.plotting_data["x"]), pen=PENS[1])
            # find the lowest point from the coefficients and move the vline to it
            lowest_pos = -coeff[1] / (2 * coeff[0])
            self.vLine.setPos(lowest_pos)
            self.lock_crosshair = True
            self.set_label()

    def move_to_pos(self):
        pos = self.vLine.getPos()[0]
        stage = self.moke.instruments['stage']
        # get the position in the linear stage ref frame
        direction_index = {"x": 0, "y": 1, "z": 2}
        direction = self.direction_stored
        move_position = stage.get_position()
        move_position[direction_index[direction]] = pos
        stage.set_position(move_position, wait=False)

    def stop_experiment(self):
        self.stop_event.set()
        self.moke.instruments['stage'].stop()

    def update_plot_data(self, position, field):
        new_data = pd.DataFrame(data=np.array(
            [[position, field]]), columns=["x", "y"])
        self.plotting_data = self.plotting_data.append(
            new_data, ignore_index=True)
        self.sigUpdatePlot.emit()

    def update_plot(self):
        try:
            if self.plotting_data.shape[0] != 0:
                # make sure that vline is visible and is not messing with the data
                vlinepos = self.vLine.getPos()[0]
                if self.plotting_data.shape[0] != 0 or (vlinepos < self.plotting_data["x"].min() and vlinepos > self.plotting_data["x"].max()):
                    self.vLine.setPos(self.plotting_data["x"].min())
                    self.set_label()
                self.plt.setLabel(
                    'bottom', 'Position [um]')
                self.plt.setLabel('left', 'Field [mT]')
                self.plt.plot(np.array(self.plotting_data['x']),
                              np.array(self.plotting_data['y']), clear=True, pen=PENS[0])
                # have to readdthe vline after clearing the plot
                self.plt.addItem(self.vLine, ignore_bounds=False)
        except:
            traceback.print_exc()

    def mouse_moved(self, pos):
        if (not self.lock_crosshair) and self.plt.sceneBoundingRect().contains(pos):
            vlinepos = self.plt.mapToView(pos).x()
            if self.plotting_data.shape[0] == 0 or (vlinepos >= self.plotting_data["x"].min() and vlinepos <= self.plotting_data["x"].max()):
                self.vLine.setPos(vlinepos)
                self.set_label()

    def set_label(self):
        pos = self.vLine.getPos()[0]
        self.label.setText("%0.2f" % pos, size='11pt')

    def mouse_clicked(self, evt):
        if self.lock_crosshair:
            self.lock_crosshair = False
        else:
            self.lock_crosshair = True


if __name__ == '__main__':
    from control.instruments.moke import Moke
    import gui.exception_handling

    # app = QApplication(sys.argv)
    # aw = FindCentre(0)
    # aw.show()
    # qApp.exec_()
    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = FindCentre(moke)
        aw.show()
        qApp.exec_()
