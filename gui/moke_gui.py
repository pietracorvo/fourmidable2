import os
import sys

import numpy as np

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
BASE_FOLDER = os.path.join(DIR_PATH, '..')
sys.path.append(os.path.join(DIR_PATH, '..'))
os.chdir(BASE_FOLDER)
# sys.path.append(os.getcwd())
from functools import partial

import hjson
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *

import display.instrument_plotting as instrument_plotting
from gui.widgets import moke_docker, movement, experiment_selection, skm_window, \
    loop_widget, stage_properties, find_centre, eucentric_protocol, move_buttons, apply_field, \
    apply_custom_field, find_max_signal, laser_button, hp_calibration, \
    fmoke_steps, microscope_steps, microscopy_analysis, microscope_imaging, camera_quantalux_settings, camera_hamamatsu_settings
from control.instruments import NIinst
from control.instruments.moke import Moke
from gui.widgets.canvas import DynamicInstrumentPlot


import traceback
import warnings
import sys

# np.warnings.filterwarnings('ignore')


QApplication.setStyle('Fusion')


class ApplicationWindow(QMainWindow):
    def __init__(self, moke):
        QMainWindow.__init__(self)
        self.moke = moke

        # Set title and delete on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Main window")

        # set window size
        screen_size = QDesktopWidget().screenGeometry()
        self.resize(int(screen_size.width()), int(
            screen_size.height() * 2 / 3))

        # load gui settings
        self.settings_file_path = os.path.join(DIR_PATH, "gui_settings.hjson")
        try:
            with open(self.settings_file_path, 'r') as file:
                self.settings_data = hjson.load(file)
        except FileNotFoundError:
            open(self.settings_file_path, 'w+')
            self.settings_data = dict()

        # try setting the data folder, fallback to default
        try:
            self.data_folder = self.settings_data["data_folder"]
        except Exception as e:
            print(f'Unable to get last data folder {self.data_folder}, default to {os.getcwd()}')
            self.data_folder = os.getcwd()
        # check that the data folder exists. Otherwise, create it
        if not os.path.isdir(self.data_folder):
            try:
                os.mkdir(self.data_folder)
            except Exception:
                print(f'Unable to create data folder {self.data_folder}, default to {os.getcwd()}')
                self.data_folder = os.getcwd()

        # set toolbars and their actions
        self.file_menu = QMenu('&File', self)
        self.file_menu.addAction('&Capture Screen', self.capture_screen,
                                 QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_S)
        self.file_menu.addAction('&Set data folder', self.set_data_folder)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)
        self.view_menu = QMenu('&View', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.view_menu)

        # add all the available docks for plotting and set the default values
        self.available_docks = {key: False for key, value in self.moke.instruments.items(
        ) if isinstance(value, NIinst)}
        self.available_docks.update({
            "quanta_camera": False,
            "hamamatsu_camera": False,
            "3D_fields": False,
            "console": False,
            "hallprobe": True,
            "temperature": False,
            "hexapole": True
        })

        # try loading docks setup from the settings, fall back to default it it fails
        try:
            if "docks" in self.settings_data and self.available_docks.keys() == self.settings_data["docks"].keys():
                self.available_docks = self.settings_data["docks"]
        except:
            self.settings_data["docks"] = self.available_docks

        # add the dock actions in the view toolbar
        self.view_menu_actions = dict()
        for k, is_open in self.available_docks.items():
            # print(k, is_open)
            action = QAction(k, self, checkable=True)
            action.setChecked(is_open)
            action.triggered.connect(partial(self.toggle_view, k))
            self.view_menu_actions[k] = action
            self.view_menu.addAction(action)

        # add menu containing experiments
        self.experiments_menu = QMenu('&Experiments', self)
        self.menuBar().addSeparator()
        # Create Menu option called Experiments
        self.menuBar().addMenu(self.experiments_menu)

        # Add "Constant Field Option"
        self.experiments_menu.addAction(
            '&Apply Constant Field', self.start_apply_field)
        self.apply_field_window = None

        # Add "Constant Field Option"
        # TODO: Revisit PID and Feedback
        self.experiments_menu.addAction(
            '&Apply Custom Field', self.start_apply_custom_field)
        self.apply_custom_field_window = None

        # Add Fourier Moke Experiment
        self.experiments_menu.addAction(
            '&Hysteresis Loops - Fourier Moke', self.start_fmoke_steps)
        self.fmoke_steps_window = None

        # Add Kerr Microscopy Measurement
        self.experiments_menu.addAction(
            '&Hysteresis Loops - Kerr Microscopy', self.start_microscope_steps)
        self.microscope_steps_window = None

        # Add Static Kerr Microscopy Imaging Measurement
        self.experiments_menu.addAction(
            '&Kerr Microscopy Imaging', self.start_microscope_imaging)
        self.microscope_imaging_window = None

        # Add analysis menu
        self.analysis_menu = QMenu('&Analysis', self)
        self.menuBar().addSeparator()
        # Create Menu option called Experiments
        self.menuBar().addMenu(self.analysis_menu)

        self.analysis_menu.addAction(
            '&MOKE Microscopy', self.start_microscopy_analysis)
        self.microscopy_analysis_window = None


        # add the calibration menu
        self.calibration_menu = QMenu('&Calibration', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.calibration_menu)

        self.calibration_menu.addAction(
            '&Hallprobe calibration', self.hallprobe_calibration)
        self.hallprobe_calibration_window = None

        self.calibration_menu.addAction(
            '&Stage properties', self.stage_properties)
        self.stage_properties_window = None

        self.calibration_menu.addAction(
            '&Find centre', self.find_centre)
        self.find_centre_window = None

        self.calibration_menu.addAction(
            '&Eucentric protocol', self.start_eucentric_protocol)
        self.eucentric_protocol_window = None

        self.help_menu = QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)
        self.help_menu.addAction('&About', self.about)

        self.main_widget = QWidget(self)

        # create plotting widget
        self.moke_docker = moke_docker.MokeDocker(self.moke,
                                                  [key for key, value in self.available_docks.items() if
                                                   value])
        self.moke_docker.sigDockClosed.connect(self.dock_closed_event)
        self.moke_docker.setMinimumSize(200, 200)

        # button to open camera settings
        self.camera_settings_window = None
        self.button_open_camera_settings = QPushButton('Open Quanta settings')
        self.button_open_camera_settings.clicked.connect(self.open_camera_settings)

        self.cameraham_settings_window = None
        self.button_open_cameraham_settings = QPushButton('Open Hamamatsu settings')
        self.button_open_cameraham_settings.clicked.connect(self.open_camerahamamatsu_settings)

        # create movement control widget
        stage = moke.instruments['stage']
        instruments_to_control = [stage]
        self.movement_control = movement.MovementControl(
            instruments_to_control)
        self.movement_control.setMinimumWidth(250)
        self.movement_control.setMaximumWidth(300)

        # add the laser control button
        #self.laser_button = laser_button.LaserButton(self.moke)

        # create movement buttons widget
        self.move_buttons = move_buttons.MovementButtons(
            self.moke.instruments["stage"])
        self.move_buttons.setMinimumWidth(200)
        self.move_buttons.setMaximumWidth(250)

        # define the widget layout
        layout = QVBoxLayout(self.main_widget)
        hlayout = QHBoxLayout()

        hlayout.addWidget(self.moke_docker)

        vlayout = QVBoxLayout()
        #vlayout.addWidget(self.laser_button)
        vlayout.addWidget(self.button_open_camera_settings)
        vlayout.addWidget(self.button_open_cameraham_settings)
        vlayout.addWidget(self.movement_control)
        vlayout.addWidget(self.move_buttons)

        # vlayout.addWidget(experiment_selector)
        hlayout.addLayout(vlayout)

        layout.addLayout(hlayout)

        self.setCentralWidget(self.main_widget)

        self.icon = QtGui.QIcon('mokelogo.ico')
        self.setWindowIcon(self.icon)

        self.showMaximized()



    def start_apply_field(self):
        self.apply_field_window = apply_field.ApplyField(self.moke)
        self.apply_field_window.show()

    def start_apply_custom_field(self):
        self.apply_custom_field_window = apply_custom_field.ApplyCustomField(
            self.moke)
        self.apply_custom_field_window.show()

    def start_fmoke_steps(self):
        self.fmoke_steps_window = fmoke_steps.ApplySteps(
            self.moke, data_folder=self.data_folder)
        self.fmoke_steps_window.show()

    def start_microscopy_analysis(self):
        self.microscopy_analysis_window = microscopy_analysis.analysis_start()
        self.microscopy_analysis_window.show()

    def start_microscope_steps(self):
        self.microscope_steps_window = microscope_steps.ApplySteps(
            self.moke, data_folder=self.data_folder)
        self.microscope_steps_window.show()

    def start_microscope_imaging(self):
        # Give self as an argument to be used inside Imaging Widget
        self.microscope_imaging_window = microscope_imaging.ImagingWidget(
            self, data_folder=self.data_folder)
        self.microscope_imaging_window.show()

    def open_camera_settings(self):
        self.camera_settings_window = camera_quantalux_settings.CameraQuantaluxSettings(self.moke)
        self.camera_settings_window.show()

    def open_camerahamamatsu_settings(self):
        self.cameraham_settings_window = camera_hamamatsu_settings.CameraHamamatsuSettings(self.moke)
        self.cameraham_settings_window.show()

    def stage_properties(self):
        self.stage_properties_window = stage_properties.StageProperties(
            self.moke.instruments['stage'])
        # connect the position defined trigger with the movement_control update values
        self.stage_properties_window.define_position.sigPositionDefined.connect(
            self.movement_control.update_values)
        self.stage_properties_window.show()

    def hallprobe_calibration(self):
        self.hallprobe_calibration_window = hp_calibration.HPCalibration(
            self.moke)
        self.hallprobe_calibration_window.show()

    def find_centre(self):
        self.find_centre_window = find_centre.FindCentre(self.moke)
        self.find_centre_window.show()

    def start_eucentric_protocol(self):
        self.eucentric_protocol_window = eucentric_protocol.EucentricProtocol(
            self.moke.instruments["stage"])
        self.eucentric_protocol_window.sigCalibrationChanged.connect(
            self.movement_control.update_values)
        self.eucentric_protocol_window.show()

    @QtCore.pyqtSlot(str)
    def dock_closed_event(self, name):
        self.available_docks[name] = False
        self.view_menu_actions[name].setChecked(False)

    def toggle_view(self, dock, state):
        if state:
            self.moke_docker.add_dock(dock)
        else:
            self.moke_docker.remove_dock(dock)
        self.available_docks[dock] = state

    def capture_screen(self):
        """Captures the GUI screen and saves it in the data folder"""
        # get the screenshot
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(self.winId())
        # get the next free filename
        i = 1
        save_path = os.path.join(self.data_folder, "screenshot%s.jpg" % i)
        while os.path.exists(save_path):
            i += 1
            save_path = os.path.join(self.data_folder, "screenshot%s.jpg" % i)
        screenshot.save(save_path)

    def set_data_folder(self):
        """Allows the user to set the data directory"""
        #print('This does nothing at the moment. Contact Luka if you want it implemented')
        folder = str(QFileDialog.getExistingDirectory(
            self, "Select Directory"))
        self.data_folder = folder

    def find_max_signal(self):
        """Moves the nanocube around to find the maximum signal"""
        self.find_max_signal_window = find_max_signal.FindMaxSignal(self.moke)
        self.find_max_signal_window.show()

    def fileQuit(self):
        sys.stdout = sys.__stdout__
        try:
            print('Saving GUI settings')
            self.settings_data["docks"] = self.available_docks
            self.settings_data["data_folder"] = self.data_folder
            with open(self.settings_file_path, 'w') as file:
                hjson.dump(self.settings_data, file)
        except:
            pass
        try:
            self.skm_window.close()
        except:
            pass
        try:
            self.loop_window.close()
        except:
            pass
        try:
            self.apply_field_window.close()
        except:
            pass
        try:
            self.apply_custom_field_window.close()
        except:
            pass
        try:
            self.fmoke_steps_window.close()
        except:
            pass
        try:
            self.camera_settings_window.close()
        except:
            pass
        try:
            self.cameraham_settings_window.close()
        except:
            pass
        try:
            self.moke_docker.close()
        except:
            pass
        self.close()
        app.closeAllWindows()

    def closeEvent(self, ce):
        self.fileQuit()

    def about(self):
        QMessageBox.about(self, "About",
                          """This program has been written by Luka Skoric (ls604@cam.ac.uk) and adapted by Alexander Rabensteiner (pietracorvo@hotmail.com) and Miguel A. Cascales Sandoval. For any questions and problems, please contact on of them."""
                          )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QtGui.QFont()
    font.setPointSize(12)
    app.setFont(font)
    import gui.exception_handling

    with Moke() as moke:
        aw = ApplicationWindow(moke)
        aw.show()
        qApp.exec_()