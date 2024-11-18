from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import pyqtSignal
import time
import traceback
from termcolor import colored


class DefinePosition(QWidget):
    sigPositionDefined = pyqtSignal()

    def __init__(self, stage):
        self.stage = stage
        QWidget.__init__(self)

        # add a group box containing controls
        input_box = QGroupBox("NOTE This has been taken over from Smaract stage and not been adapted to Nanocube yet!\n\nDefine Position")

        # add x, y and z input fields
        position_label = dict()
        self.position_value = dict()
        for key in stage.direction_labels:
            position_label[key] = QLabel(input_box)
            position_label[key].setText(key + ':')
            self.position_value[key] = QLineEdit(self)

        # write the values
        self.update_values()

        # add move button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_values)
        # add define button
        self.define_button = QPushButton("Define Position")
        self.define_button.clicked.connect(self.define_button_clicked)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(input_box)
        input_box.setSizePolicy(QSizePolicy.Expanding,
                                QSizePolicy.Expanding)

        input_layout = QGridLayout()

        N = len(position_label.items())  # number of entries
        for i, label, value in zip(range(2, N + 2), position_label.values(), self.position_value.values()):
            input_layout.addWidget(label, i, 0, alignment=QtCore.Qt.AlignRight)
            input_layout.addWidget(value, i, 1, alignment=QtCore.Qt.AlignLeft)
            input_layout.addItem(QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), i, 2)

            label.setMaximumWidth(50)
            value.setMaximumWidth(200)

        input_layout.addWidget(self.refresh_button, i + 1,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.define_button, i + 2,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)

        input_box.setLayout(input_layout)
        self.setLayout(main_layout)

        # stop movement on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMaximumHeight(500)

    def define_button_clicked(self, append_to_last=True):
        """Defines the stage to the values in input fields"""
        reply = QMessageBox.question(self, 'Double check',
                                     """This will change the current coordinates of the stage and can affect calibration.
                                     If you want to keep eucentric calibration, please make sure that you are at 0 degrees rotation. Continue?""", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.stage.define_position(self.get_values())
        self.sigPositionDefined.emit()
        # time.sleep(0.1)
        # self.fileQuit()

    def get_values(self):
        try:
            result = [float(p.text()) for p in self.position_value.values()]
        except ValueError as err:
            print('All entries need to be numbers')
            raise err
        return result

    def update_values(self):
        """Gets the position and writes it in the input fields"""
        position = self.stage.get_position()
        for p, value in zip(position, self.position_value.values()):
            value.setText(f'{p:.2f}')

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()


class ReferencePosition(QWidget):

    def __init__(self, stage):
        self.stage = stage
        QWidget.__init__(self)

        # add a group box containing controls
        reference_box = QGroupBox("Reference")

        # add x, y and z reference fields
        self.reference_table = QTableWidget()
        self.reference_table.setRowCount(4)
        self.reference_table.setColumnCount(2)
        self.fill_table()

        # add reference direction button
        self.direction_dropdown = QComboBox()
        self.direction_dropdown.addItems(self.stage.direction_labels)

        self.reverse_direction_check = QCheckBox("&Reverse", reference_box)

        self.reference_button = QPushButton("Reference")
        self.reference_button.clicked.connect(self.reference_direction)

        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self.calibrate_direction)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_stages)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(reference_box)
        reference_box.setSizePolicy(QSizePolicy.Expanding,
                                    QSizePolicy.Expanding)

        input_layout = QGridLayout()

        input_layout.addWidget(self.reference_table, 0,
                               0, 1, 2, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.direction_dropdown, 1, 0)
        input_layout.addWidget(self.reverse_direction_check, 1, 1)
        input_layout.addWidget(self.reference_button, 2, 0)
        input_layout.addWidget(self.calibrate_button, 3, 0)
        input_layout.addWidget(self.stop_button, 4, 0)

        reference_box.setLayout(input_layout)
        self.setLayout(main_layout)

        # stop movement on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMaximumHeight(500)

        # update the table every 1 second
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.fill_table)
        self._timer.start(1000)

    def fill_table(self):
        self.reference_table.setHorizontalHeaderLabels(
            ["Direction", "Referenced"])
        is_referenced = self.stage.is_referenced()
        i = 0
        for ref, lbl in zip(is_referenced, self.stage.direction_labels):
            self.reference_table.setItem(i, 0, QTableWidgetItem(lbl))
            self.reference_table.setItem(i, 1, QTableWidgetItem(str(ref)))
            i += 1

        self.reference_table.resizeColumnsToContents()
        self.reference_table.resizeRowsToContents()

    def reference_direction(self):
        direction = self.direction_dropdown.currentText()
        reverse = self.reverse_direction_check.isChecked()
        print('Referencing direction {} in reverse = {}'.format(direction, reverse))
        self.stage.reference_axis(direction, reverse=reverse)

    def calibrate_direction(self):
        direction = self.direction_dropdown.currentText()
        reverse = self.reverse_direction_check.isChecked()
        print('Calibrating direction {} in reverse = {}'.format(direction, reverse))
        print(direction)
        print(reverse)
        self.stage.calibrate_axis(direction, reverse=reverse)

    def stop_stages(self):
        self.stage.stop()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()


class VelocitySetter(QWidget):
    sigPositionDefined = pyqtSignal()

    def __init__(self, stage):
        self.stage = stage
        QWidget.__init__(self)

        # add a group box containing controls
        input_box = QGroupBox("Set Velocity")

        # set the scale for velocity (1 is pm/ndeg per s)
        self.scale = 10**6
        # add x, y and z input fields
        velocity_label = dict()
        self.velocity_value = dict()
        for key in stage.direction_labels:
            velocity_label[key] = QLabel(input_box)
            # this should be done by checking the units, but can't be bothered
            if key != "phi":
                velocity_label[key].setText(key + ' [um/s]:')
            else:
                velocity_label[key].setText(key + ' [mdeg/s]:')
            self.velocity_value[key] = QLineEdit(self)

        # write the values
        self.update_values()

        # add move button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_values)
        # add define button
        self.define_button = QPushButton("Set velocity")
        self.define_button.clicked.connect(self.set_velocity_button_clicked)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(input_box)
        input_box.setSizePolicy(QSizePolicy.Expanding,
                                QSizePolicy.Expanding)

        input_layout = QGridLayout()

        N = len(velocity_label.items())  # number of entries
        for i, label, value in zip(range(2, N + 2), velocity_label.values(), self.velocity_value.values()):
            input_layout.addWidget(label, i, 0, alignment=QtCore.Qt.AlignLeft)
            input_layout.addWidget(value, i, 1, alignment=QtCore.Qt.AlignRight)
            input_layout.addItem(QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), i, 2)

            label.setMaximumWidth(50)
            value.setMaximumWidth(200)

        input_layout.addWidget(self.refresh_button, i + 1,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.define_button, i + 2,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)

        input_box.setLayout(input_layout)
        self.setLayout(main_layout)

        # stop movement on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMaximumHeight(500)

    def update_values(self):
        """Gets the position and writes it in the input fields"""
        velocity = self.stage.get_velocity()
        for v, value in zip(velocity, self.velocity_value.values()):
            value.setText(f'{v/self.scale:.2f}')

    def get_values(self):
        try:
            result = [int(float(p.text())) * self.scale
                      for p in self.velocity_value.values()]
            print('Set velocity to: ', result)
        except ValueError as err:
            print('All entries need to be numbers')
            raise err
        return result

    def set_velocity_button_clicked(self):
        self.stage.set_velocity(self.get_values())


class StageProperties(QWidget):

    def __init__(self, stage):
        self.stage = stage
        QWidget.__init__(self)

        self.define_position = DefinePosition(stage)
        self.reference_position = ReferencePosition(stage)
        self.set_velocity = VelocitySetter(stage)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.define_position)
        main_layout.addWidget(self.reference_position)
        main_layout.addWidget(self.set_velocity)

        self.setLayout(main_layout)

        # stop movement on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)


if __name__ == '__main__':
    import sys
    import os
    sys.path.append(os.getcwd())

    from unittest.mock import Mock
    stage = Mock()
    stage.get_position = Mock(return_value=[1, 2, 3, 4])
    stage.get_velocity = Mock(return_value=[10, 22, 33, 44])
    stage.is_referenced = Mock(return_value=[True, False, True, False])
    stage.direction_labels = ["x", "y", "z", "phi"]
    app = QApplication(sys.argv)
    aw = StageProperties(stage)
    aw.show()
    qApp.exec_()
    # from control.instruments.moke import Moke

    # with Moke() as moke:
    #     app = QApplication(sys.argv)
    #     stage = moke.instruments['stage']
    #     aw = DefinePosition(stage)
    #     aw.show()
    #     qApp.exec_()
