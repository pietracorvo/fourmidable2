import numpy as np
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from experiments.skm import *
from data.signal_generation import get_const_signal
from copy import copy
from matplotlib import cm
import threading
import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree


class SkmWidget(QWidget):
    def __init__(self, moke):
        self.moke = moke
        self.stage = moke.instruments['stage']
        QWidget.__init__(self)

        self.experiment_parameters = {
            #"side_length": 30,
            "X_size": 30,
            "Y_size": 30,
            "Z_size": 0,
            "resolution": 3,
            "voxel_size": 3,
            "integration_time": 100,
            "speed": 700,
            "acceleration": 100000000,
            "duration": 5,
        }

        params_list = [
            ExperimentParams(name='Experiment Parameters'),
            {'name': 'Running the experiment', 'type': 'group', 'children': [
                {'name': 'Run', 'type': 'action'},
            ]}
        ]

        ## Create tree of Parameter objects
        self.params = Parameter.create(name='params', type='group', children=params_list)
        self.params.sigTreeStateChanged.connect(self.params_changed)

        # add the parameter tree for editing the parameters
        self.paramtree = ParameterTree()
        self.paramtree.setParameters(self.params, showTop=False)
        self.paramtree.setMaximumWidth(350)

        self.heatmap_data = np.zeros((500, 500))
        self.pos_data = np.zeros((1, 4))
        self.woll_1_data = np.zeros((1, 1))
        self.woll_2_data = np.zeros((1, 1))
        self.woll_3_data = np.zeros((1, 1))
        self.woll_4_data = np.zeros((1, 1))

        self.X_size = 30
        self.Y_size = 30
        self.resolution = 3
        self.integration_time = 100
        self.Z_size = 0
        self.voxel_size = 3
        self.acceleration = 1000000

        self.data_source = 'Arm 1'

        self.loaded = 0

        # self.heatmap_data[:200, :200] *= 0
        self.graphicswidget = pg.GraphicsLayoutWidget()
        self.graphicswidget.show()
        self.viewbox = self.graphicswidget.addViewBox(lockAspect=True)
        # self.graphicswidget.addItem(self.viewbox)
        self.img = pg.ImageItem(self.heatmap_data, border='w')

        # Get the colormap
        colormap = cm.get_cmap("jet")  # cm.get_cmap("CMRmap")
        colormap._init()
        lut = (colormap._lut * 255).view(np.ndarray)
        self.img.setLookupTable(lut)

        self.viewbox.addItem(self.img)
        # add the crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.lock_crosshair = False
        self.viewbox.addItem(self.vLine)
        self.viewbox.addItem(self.hLine)
        # add the contrast brightness
        self.graphicswidget.nextColumn()
        self.cont_bright = pg.HistogramLUTItem()
        self.cont_bright.lut = lut
        self.cont_bright.setImageItem(self.img)
        self.graphicswidget.addItem(self.cont_bright)

        self.graphicswidget.setMinimumWidth(500)

        # add the position control
        # add a group box containing controls
        self.input_box = QGroupBox("Position")
        self.x_label = QLabel(self.input_box)
        self.x_label.setText('x: ')
        self.x_input = QLineEdit()
        self.x_input.setText('0')
        self.y_label = QLabel(self.input_box)
        self.y_label.setText('y: ')
        self.y_input = QLineEdit()
        self.y_input.setText('0')
        self.max_button = QPushButton("Maximum")
        self.max_button.clicked.connect(self.find_max)
        self.max_button.setEnabled(False)
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.go_button_clicked)
        self.data_sel = QComboBox()
        self.data_sel.addItem("Sum")
        self.data_sel.addItem("Diff")
        self.data_sel.addItem("Avg")
        self.data_sel.addItem("Det 1")
        self.data_sel.addItem("Det 2")
        self.data_sel.activated.connect(self.update_plot)
        self.sel_label = QLabel(self.input_box)
        self.sel_label.setText('Data:')
        self.slice_sel = QSlider(Qt.Horizontal)
        self.slice_sel.valueChanged.connect(self.update_slice)
        self.slice_sel.setTickPosition(QSlider.TicksBelow)
        self.slice_sel.setEnabled(False)
        self.slice_label = QLabel(self.input_box)
        self.slice_label.setText('z:')
        self.slice_input = QLineEdit()
        self.slice_input.textChanged.connect(self.update_slider)
        self.slice_input.setText('0')
        self.data_val_label = QLabel(self.input_box)
        self.data_val_label.setText('Value (mV): ')
        self.data_val = QLineEdit()
        self.data_val.setText('0')
        self.arm_sel = QComboBox()
        self.arm_sel.addItem("Arm 1")
        self.arm_sel.addItem("Arm 2")
        self.arm_sel.activated.connect(self.update_plot)
        self.save_button = QPushButton("Save...")
        self.save_button.clicked.connect(self.save_f)
        self.load_button = QPushButton("Load...")
        self.load_button.clicked.connect(self.load_f)

        # add mouse movement
        self.graphicswidget.scene().sigMouseMoved.connect(self.mouse_moved)
        self.graphicswidget.scene().sigMouseClicked.connect(self.mouse_clicked)

        layout = QHBoxLayout()
        layout.addWidget(self.paramtree)
        layout.addWidget(self.graphicswidget)

        input_layout = QGridLayout(self.input_box)
        input_layout.addWidget(self.x_label, 0, 0)
        input_layout.addWidget(self.x_input, 0, 1)
        input_layout.addWidget(self.y_label, 1, 0)
        input_layout.addWidget(self.y_input, 1, 1)
        input_layout.addWidget(self.slice_label, 2, 0)
        input_layout.addWidget(self.slice_sel, 2, 2)
        input_layout.addWidget(self.slice_input, 2, 1)
        input_layout.addWidget(self.max_button, 3, 2)
        input_layout.addWidget(self.go_button, 3, 1)
        input_layout.addWidget(self.sel_label, 4, 0)
        input_layout.addWidget(self.data_sel, 4, 1)
        input_layout.addWidget(self.arm_sel, 4, 2)
        input_layout.addWidget(self.data_val, 5, 1)
        input_layout.addWidget(self.data_val_label, 5, 0)
        input_layout.addWidget(self.save_button, 6, 0)
        input_layout.addWidget(self.load_button, 6, 1)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)
        input_layout.setColumnStretch(2, 1)

        layout.addWidget(self.input_box)

        self.setLayout(layout)
        self.resize(1100, 500)

    def params_changed(self, param, changes):
        for param, change, data in changes:
            if change == "value":
                self.experiment_parameters[param.name()] = data
            elif change == "activated" and param.name() == "Run":
                self.run_skm()

    def skm_worker(self):
        # run the experiment
        print('Running the experiment...')

        #skm_map_smaract made by Angelo Mottolese, previous skm_map for Nanocube by Luka
        self.pos_data, self.woll_1_data, self.woll_2_data, self.woll_3_data, self.woll_4_data = skm_map_smaract(self.moke, self.experiment_parameters['resolution'], self.experiment_parameters['voxel_size'], self.experiment_parameters['X_size']/self.experiment_parameters['resolution'], self.experiment_parameters['Y_size']/self.experiment_parameters['resolution'], self.experiment_parameters['Z_size'] / self.experiment_parameters['voxel_size'], self.experiment_parameters['speed'], 0.001 * self.experiment_parameters['integration_time'], self.experiment_parameters['acceleration'])
        plot = self.data_sel.currentText()
        maximum = int(self.experiment_parameters['Z_size'])
        if maximum > 0:
            self.slice_sel.setEnabled(True)
        self.slice_sel.setMaximum(maximum)
        self.slice_sel.setMinimum(0)
        self.slice_sel.setTickInterval(int(self.experiment_parameters['voxel_size']))
        self.slice_sel.setSingleStep(int(self.experiment_parameters['voxel_size']))
        self.slice_sel.setPageStep(int(self.experiment_parameters['voxel_size']))
        slice_n = int(self.slice_sel.value() / self.experiment_parameters['voxel_size'])
        self.heatmap_data = process_skm(self.pos_data, self.woll_1_data[slice_n], self.woll_2_data[slice_n], int(self.experiment_parameters['X_size'] / self.experiment_parameters['resolution']), int(self.experiment_parameters['Y_size'] / self.experiment_parameters['resolution']), plot)
        # get the colormap
        # set the image data
        self.img.updateImage(image=self.heatmap_data, levels=(np.min(self.heatmap_data), np.max(self.heatmap_data)))
        #self.side_length = copy(self.experiment_parameters['side_length'])
        self.X_size = copy(self.experiment_parameters['X_size'])
        self.Y_size = copy(self.experiment_parameters['Y_size'])
        self.resolution = copy(self.experiment_parameters['resolution'])
        # enable the max button
        self.max_button.setEnabled(True)
        self.loaded = 0

    def run_skm(self):
        self.skm_thread = threading.Thread(target=self.skm_worker)
        self.skm_thread.daemon = True
        self.skm_thread.start()
        self.initial_position = self.stage.get_position()

    def find_max(self):
        coords = np.array(np.unravel_index(self.heatmap_data.argmax(), self.heatmap_data.shape))
        coords_pos = self.coords_to_pos(coords)
        self.x_input.setText(f'{coords_pos[0]:.2f}')
        self.y_input.setText(f'{coords_pos[1]:.2f}')
        self.vLine.setPos(coords[0])
        self.hLine.setPos(coords[1])
        self.lock_crosshair = True

    def coords_to_pos(self, coords):
        #return np.array(coords) * self.side_length / np.array(self.heatmap_data.shape)
        center = np.array([0.5 * self.X_size / self.resolution, 0.5 * self.Y_size / self.resolution])
        coords = np.asarray(coords)
        return np.array(np.subtract(coords, center)) * [self.resolution, self.resolution]

    def go_button_clicked(self):
        # get the values
        x = float(self.x_input.text())
        y = float(self.y_input.text())
        z = float(self.slice_input.text())
        # move to that value
        #self.nanocube.set_position([x, y, 0])
        pos = self.initial_position + [x, y, z, 0]
        self.stage.set_position(pos, False, False)

    def mouse_moved(self, pos):
        if (not self.lock_crosshair) and self.img.sceneBoundingRect().contains(pos):
            #mapping are the coords in pixel units (floating point for enhanced precision)
            mapping = self.img.mapFromScene(pos)
            coords = [mapping.x(), mapping.y()]
            coords_pos = self.coords_to_pos(coords)
            self.x_input.setText(f'{coords_pos[0]:.2f}')
            self.y_input.setText(f'{coords_pos[1]:.2f}')
            self.vLine.setPos(coords[0])
            self.hLine.setPos(coords[1])
            hm = self.heatmap_data
            value = hm[int(mapping.x()), int(mapping.y())]
            self.data_val.setText(f'{value:.4f}')

    def mouse_clicked(self, evt):
        if self.lock_crosshair:
            self.lock_crosshair = False
        else:
            self.lock_crosshair = True

    def update_plot(self):
        position = np.asarray(self.pos_data).size
        if position > 4 or self.loaded == 1:
            plot = self.data_sel.currentText()
            slice_n = int(self.slice_sel.value() / self.experiment_parameters['voxel_size'])
            if self.arm_sel.currentIndex() == 0:
                data_1, data_2 = self.woll_1_data[slice_n], self.woll_2_data[slice_n]
            else:
                data_1, data_2 = self.woll_3_data[slice_n], self.woll_4_data[slice_n]
            print(slice_n, data_2)
            self.heatmap_data = process_skm(self.pos_data, data_1, data_2, int(self.experiment_parameters['X_size'] / self.experiment_parameters['resolution']), int(self.experiment_parameters['Y_size'] / self.experiment_parameters['resolution']), plot)
            self.img.updateImage(image=self.heatmap_data, levels=(np.min(self.heatmap_data), np.max(self.heatmap_data)))

    def update_slider(self):
        new = int(float(self.slice_input.text()))
        self.slice_sel.setValue(new)
        self.update_plot()

    def update_slice(self):
        self.slice_input.setText(f'{self.slice_sel.value():.2f}')
        self.update_plot()

    def save_f(self):
        filename = QFileDialog(self, "Save reflectivity map datafile", "C:/", ".dat")
        filename.setDefaultSuffix(".dat")
        if filename.exec():
            save_header = str(len(self.woll_1_data)) + " : " + str(len(self.woll_1_data[0])) + " : " + str(int(self.experiment_parameters['X_size'] / self.experiment_parameters['resolution'])) + " " + str(int(self.experiment_parameters['Y_size'] / self.experiment_parameters['resolution']))
            tot = len(self.woll_1_data) * len(self.woll_1_data[0])
            data = (self.woll_1_data.flatten(), self.woll_2_data.flatten(), self.woll_3_data.flatten(), self.woll_4_data.flatten())
            print(save_header)
            savefile = filename.selectedFiles()
            np.savetxt(savefile[0], data, header=save_header)

    def load_f(self):
        filename = QFileDialog.getOpenFileName(self, "Open reflectivity map datafile", "C:/", "")
        f = open(filename[0], "r")
        header = f.readline().split()
        f.close()
        # 1 : 9 W,H: 3.0 3.0
        W = int(header[5])
        H = int(header[6])
        D = int(header[1])
        #GOT TO IMPORT EVERY PARAMETER!!!!!!!!!!!!!!!!
        #self.experiment_parameters['X_size'] = W
        #self.experiment_parameters['Y_size'] = H
        self.experiment_parameters['Z_size'] = D
        (w_1, w_2, w_3, w_4) = np.genfromtxt(filename[0], skip_header=1)
        self.woll_1_data = np.reshape(w_1, ((D, W * H)))
        self.woll_2_data = np.reshape(w_2, ((D, W * H)))
        self.woll_3_data = np.reshape(w_3, ((D, W * H)))
        self.woll_4_data = np.reshape(w_4, ((D, W * H)))
        self.loaded = 1
        maximum = int((D-1) * int(self.experiment_parameters['voxel_size']))
        if maximum > 0:
            self.slice_sel.setEnabled(True)
        self.slice_sel.setMaximum(maximum)
        self.update_plot()

# duration and speed parameters which are mutually dependent
class ExperimentParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pTypes.GroupParameter.__init__(self, **opts)

        #self.addChild({'name': 'side_length', 'type': 'float', 'value': 30, 'suffix': 'um', 'step': 0.1})
        self.addChild({'name': 'X_size', 'type': 'float', 'value': 30, 'suffix': 'um', 'step': 0.1})
        self.addChild({'name': 'Y_size', 'type': 'float', 'value': 30, 'suffix': 'um', 'step': 0.1})
        self.addChild({'name': 'Z_size', 'type': 'float', 'value': 0, 'suffix': 'um', 'step': 0.1})
        self.addChild({'name': 'resolution', 'type': 'float', 'value': 3, 'suffix': 'um', 'step': 0.01})
        self.addChild({'name': 'voxel_size', 'type': 'float', 'value': 3, 'suffix': 'um', 'step': 0.01})
        self.addChild({'name': 'integration_time', 'type': 'float', 'value': 100, 'suffix': 'ms', 'step': 10})
        self.addChild({'name': 'speed', 'type': 'float', 'value': 700, 'suffix': 'um/s', 'step': 1})
        self.addChild({'name': 'acceleration', 'type': 'float', 'value': 10000000000, 'suffix': 'um/s^2', 'step': 1})
        self.addChild({'name': 'duration', 'type': 'float', 'value': 5, 'suffix': 'min', 'step': 1})
        self.speed = self.param('speed')
        self.acceleration = self.param('acceleration')
        self.duration = self.param('duration')
        self.X_size = self.param('X_size')
        self.Y_size = self.param('Y_size')
        self.Z_size = self.param('Z_size')
        self.voxel_size = self.param('voxel_size')
        self.resolution = self.param('resolution')
        self.speed.sigValueChanged.connect(self.speedChanged)
        self.integration_time.sigValueChanged.connect(self.timeChanged)
        self.Z_size.sigValueChanged.connect(self.speedChanged)
        self.voxel_size.sigValueChanged.connect(self.speedChanged)
        self.duration.sigValueChanged.connect(self.durationChanged)
        self.resolution.sigValueChanged.connect(self.resolutionChanged)
        self.X_size.sigValueChanged.connect(self.side_lengthChanged)
        self.Y_size.sigValueChanged.connect(self.side_lengthChanged)
        self.speedChanged()

    def speedChanged(self):
        tot_time = (self.Z_size.value()/self.voxel_size.value() + 1) * (self.total_l / self.speed.value() + self.X_size.value() * self.Y_size.value() * self.integration_time.value() * 0.001)
        tot_time /= 60.0
        self.duration.setValue(tot_time, blockSignal=self.durationChanged)

    def durationChanged(self):
        self.speed.setValue(self.total_l / (self.duration.value() * 60.0), blockSignal=self.speedChanged)

    def resolutionChanged(self):
        self.speedChanged()

    def side_lengthChanged(self):
        self.speedChanged()

    def timeChanged(self):
        self.speedChanged()

    @property
    def total_l(self):
        return self.X_size.value() * self.Y_size.value() / self.resolution.value()


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    import gui.exception_handling

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = SkmWidget(moke)
        aw.show()
        qApp.exec_()
