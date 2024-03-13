from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtProperty, pyqtSignal
from PyQt5 import QtCore, QtWidgets

import numpy as np
import hjson
import copy

from control.calibration.calibrations import InstrumentCalibration, StageSampleRefCalib


class EucentricProtocol(QtWidgets.QWizard):
    sigCalibrationChanged = pyqtSignal()

    def __init__(self, stage, parent=None):
        super(EucentricProtocol, self).__init__(parent)
        self.stage = stage
        self.initial_calibration = stage.calibration
        self.position1 = None
        self.position2 = None
        self.rotation_axis_displacement = None
        # flag keeping track if the user finished normally or aborted
        self.finished_normally = False
        self.button(QtWidgets.QWizard.NextButton).clicked.connect(
            self.next_pressed)
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(
            self.finish_pressed)
        self.setOption(QtWidgets.QWizard.NoCancelButton)

        self.addPage(Page1(self))
        self.addPage(Page2(self))
        self.addPage(Page3(self))
        self.addPage(Page4(self))
        self.setWindowTitle("Eucentric protocol wizard")

    def closeEvent(self, ce):
        self.apply_calculated_calibration()
        self.close()

    def apply_calculated_calibration(self):
        if self.finished_normally:
            parameters = {
                "zero_angle": 0,
                "rotation_axis_displacement": list(self.rotation_axis_displacement),
                "zero_position_displacement": list(self.zero_disp)
            }
            self.stage.calibration = StageSampleRefCalib(
                parameters, self.stage)
            print('Calibration applied')

            with open('eucentric_calibration.hjson', 'w') as file:
                hjson.dump(parameters, file)

            self.sigCalibrationChanged.emit()
        else:
            self.stage.calibration = self.initial_calibration
            self.sigCalibrationChanged.emit()

    def finish_pressed(self):
        self.finished_normally = True
        self.apply_calculated_calibration()

        """ This is if we want to handle the file programically
        parameters = {
            "zero_angle": 0,
            "rotation_axis_displacement": list(self.rotation_axis_displacement),
        }
        # # save the rotation axis displacement
        # path = 'settings_file.hjson'
        # # get the old settings and save backup
        # with open(path, 'r') as file:
        #     settings_data = hjson.load(file)
        # with open(path + "~", 'w') as file:
        #     hjson.dump(settings_data, file)
        # # define the new calibration
        # newcalibration = {
        #     "type": "StageSampleRefCalib",
        #     "parameters": parameters,
        #     "subinstruments": "stage"
        # }
        # settings_data["instruments"]["stage"]["calibration"] = newcalibration
        # # save the new calibration
        # with open(path, 'w') as file:
        #     hjson.dump(settings_data, file)
        # # 
        # print('finished')"""

    def next_pressed(self):
        if self.currentId() == 1:
            self.stage.calibration = InstrumentCalibration()
            self.sigCalibrationChanged.emit()
            print('Calibration set to default')
        elif self.currentId() == 2:
            self.position1 = self.stage.get_position()
            print('Position 1: ', self.position1)
        elif self.currentId() == 3:
            self.position2 = self.stage.get_position()
            print('Position 2: ', self.position2)
            self.get_rotation_axis_displacement()
            self.get_zero_disp()

            self.page(
                3).rotation_axis_displacement = self.rotation_axis_displacement
            self.page(
                3).zero_disp = self.zero_disp
            self.page(3).initializePage()

    def get_matrix(self, angle_deg):
        """get the rotation matrix"""
        angle = np.radians(angle_deg)
        c, s = np.cos(angle), np.sin(angle)
        R = np.array(((c, s), (-s, c)))
        return R

    def get_rotation_axis_displacement(self):
        theta1 = self.position1[3]
        theta2 = self.position2[3]
        x1 = np.array(self.position1)[[0, 2]]
        x2 = np.array(self.position2)[[0, 2]]
        R1 = self.get_matrix(-theta1)
        R2 = self.get_matrix(-theta2)

        self.rotation_axis_displacement = np.linalg.inv(R2 - R1).dot(
            R2.dot(x2) - R1.dot(x1))
        print('Rotation displacement: ', self.rotation_axis_displacement)

    def get_zero_disp(self):
        theta2 = self.position2[3]
        x2 = np.array(self.position2)[[0, 2]]
        R2 = self.get_matrix(theta2)
        d = self.rotation_axis_displacement

        self.zero_disp = R2.transpose().dot(d - x2) - d
        print('Zero displacement: ', self.zero_disp)


class Page1(QtWidgets.QWizardPage):
    "Align the lenses and set the calibration to default"

    def __init__(self, parent=None):
        super(Page1, self).__init__(parent)
        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.NextButton, 'Continue')

    def initializePage(self):
        self.label1.setText(
            """Use a rough sample to make sure the laser and both lenses are focused at the same line of points.""")
        self.label2.setText(
            "Continuing will remove the current eucentric calibration and will set the stage calibration to default")


class Page2(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(Page2, self).__init__(parent)

        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.NextButton,
                           'Save current position')

    def initializePage(self):
        self.label1.setText(
            "Make sure the laser is in the middle of both camera images.")


class Page3(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(Page3, self).__init__(parent)

        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.NextButton,
                           'Save current position')

    def initializePage(self):
        self.label1.setText("""Rotate by a large angle and refocus the image only by moving the stage.
Make sure that you are focused at the same point as before (i.e. laser in the middle of the screen""")
        self.label2.setText("Continuing will save the current position")


class Page4(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(Page4, self).__init__(parent)
        self.rotation_axis_displacement = [0, 0]
        self.zero_disp = [0, 0]

        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        self.label3 = QtWidgets.QLabel()
        self.label4 = QtWidgets.QLabel()
        self.label5 = QtWidgets.QLabel()
        self.label6 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        layout.addWidget(self.label3)
        layout.addWidget(self.label4)
        layout.addWidget(self.label5)
        layout.addWidget(self.label6)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.FinishButton,
                           'Apply')

    def initializePage(self):
        self.label1.setText(
            """The eucentric calibration is giving the rotation axis displacement to be:""")
        self.label2.setText("[{:.2f}, {:.2f}]".format(
            *self.rotation_axis_displacement))
        self.label3.setText(
            """And the zero position displacement: """)
        self.label4.setText("[{:.2f}, {:.2f}]".format(*self.zero_disp))

        self.label5.setText("Pressing finish will apply this calibration")
        self.label6.setText(
            "For future use, put the above numbers in settings")


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    wizard = EucentricProtocol(0)
    wizard.show()
    sys.exit(app.exec_())
