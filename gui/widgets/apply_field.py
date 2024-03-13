from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QSizePolicy
import numpy as np

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from data.signal_generation import get_const_signal
from experiments.basic import zero_magnet
from experiments.basic import deGauss
from PyQt5.QtCore import QThread, pyqtSignal


class deGaussThread(QThread):
    signal = pyqtSignal()

    def __init__(self, moke):
        QThread.__init__(self)
        self.moke = moke

    # run method gets called when we start the thread
    def run(self):
        deGauss(self.moke)
        self.signal.emit()


class ApplyField(QWidget):
    def __init__(self, moke):
        self.hexapole = moke.instruments['hexapole']
        self.moke = moke
        QWidget.__init__(self)

        # add a group box containing controls
        input_box = QGroupBox("Fields")
        direction_list = ["x", "y", "z"]

        # add x, y and z input fields
        direction_label = dict()
        self.field_values = dict()
        for direction in direction_list:
            direction_label[direction] = QLabel(input_box)
            direction_label[direction].setText(direction + ':')
            self.field_values[direction] = QLineEdit(self)
            self.field_values[direction].setText('0')
            # add shortcut to move button
            self.field_values[direction].returnPressed.connect(
                self.apply_fields)
            self.field_values[direction].installEventFilter(self)

        # add apply fields button
        self.apply_button = QPushButton("Apply fields")
        self.apply_button.clicked.connect(self.apply_fields)
        # add stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_fields)
        # add degauss button
        self.degauss_button = QPushButton("deGauss")
        self.degauss_button.clicked.connect(self.apply_degaussing)
        # add import signal button
        self.import_button = QPushButton("Import signal")
        self.import_button.clicked.connect(self.import_signal)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(input_box)
        input_box.setSizePolicy(QSizePolicy.Expanding,
                                QSizePolicy.Expanding)

        input_layout = QGridLayout()

        N = len(direction_label.items())  # number of entries
        for i, label, value in zip(range(3, N + 3), direction_label.values(), self.field_values.values()):
            input_layout.addWidget(label, i, 0, alignment=QtCore.Qt.AlignRight)
            input_layout.addWidget(value, i, 1, alignment=QtCore.Qt.AlignLeft)
            input_layout.addItem(QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), i, 2)
            label.setMaximumWidth(50)
            value.setMaximumWidth(200)

        input_layout.addWidget(self.apply_button, i + 1,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.stop_button, i + 2,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.degauss_button, i + 3,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)

        input_box.setLayout(input_layout)
        self.setLayout(main_layout)

        # define the degaussing thread
        self.degauss_thread = deGaussThread(self.moke)
        self.degauss_thread.signal.connect(self.set_subwidget_state)

    def get_input_values(self):
        """Gets the set field values as a list"""
        try:
            result = [float(p.text()) for p in self.field_values.values()]
        except ValueError as err:
            print('All entries need to be numbers')
            raise err
        return result

    def apply_fields(self):
        """Applies the set field values"""
        values = self.get_input_values()
        self.hexapole.stage_data(get_const_signal(values), 1)

    def stop_fields(self):
        """Applies 0s to the field values"""
        zero_magnet(self.moke)

    def set_subwidget_state(self, state=True):
        """Disables or enables the state of all subwidgets based on bool state"""
        self.apply_button.setEnabled(state)
        self.stop_button.setEnabled(state)
        self.degauss_button.setEnabled(state)
        for field in self.field_values.values():
            field.setEnabled(state)

    def apply_degaussing(self):
        """Applies degaussing procedure"""
        self.set_subwidget_state(False)
        self.degauss_thread.start()

    def import_signal(self):
        """Imports a signal file"""
        fname = QFileDialog.getOpenFileName(self, 'Open file')
        signal = np.loadtxt(fname)


if __name__ == '__main__':
    from control.instruments.moke import Moke

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = ApplyField(moke)
        aw.show()
        qApp.exec_()
