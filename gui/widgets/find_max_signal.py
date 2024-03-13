from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import traceback

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
import threading
from experiments.find_maximum import find_maximum
from warnings import warn


class FindMaxThread(QThread):

    def __init__(self, moke, get_values, stop_event):
        QThread.__init__(self)
        self.moke = moke
        self.get_values = get_values
        self.stop_event = stop_event

    # run method gets called when we start the thread
    def run(self):
        self.stop_event.clear()
        distance, start_step, end_step = self.get_values()
        find_maximum(self.moke, distance, start_step,
                     end_step, self.stop_event)


class FindMaxSignal(QWidget):
    def __init__(self, moke):
        self.moke = moke
        QWidget.__init__(self)
        # add a group box containing controls
        input_box = QGroupBox("Parameters")
        input_box.setSizePolicy(QSizePolicy.Expanding,
                                QSizePolicy.Expanding)

        input_layout = QVBoxLayout()

        max_dist_label = QLabel(input_box)
        max_dist_label.setText("Maximum distance [um]")
        self.max_dist_lineedit = QLineEdit(input_box)
        self.max_dist_lineedit.setText('10')
        max_dist_layout = QHBoxLayout()
        max_dist_layout.addWidget(max_dist_label)
        max_dist_layout.addWidget(self.max_dist_lineedit)
        input_layout.addLayout(max_dist_layout)

        start_step_label = QLabel(input_box)
        start_step_label.setText("Starting step [um]")
        self.start_step_lineedit = QLineEdit(input_box)
        self.start_step_lineedit.setText('1')
        start_step_layout = QHBoxLayout()
        start_step_layout.addWidget(start_step_label)
        start_step_layout.addWidget(self.start_step_lineedit)
        input_layout.addLayout(start_step_layout)

        end_step_label = QLabel(input_box)
        end_step_label.setText("Minimum step [um]")
        self.end_step_lineedit = QLineEdit(input_box)
        self.end_step_lineedit.setText('0.2')
        end_step_layout = QHBoxLayout()
        end_step_layout.addWidget(end_step_label)
        end_step_layout.addWidget(self.end_step_lineedit)
        input_layout.addLayout(end_step_layout)

        # add apply fields button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        # add stop button
        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop)
        # add go back button
        self.go_back_button = QPushButton("Go back")
        self.last_position = self.get_position()
        self.go_back_button.clicked.connect(self.go_back)

        input_layout.addWidget(self.start_button)
        input_layout.addWidget(stop_button)
        input_layout.addWidget(self.go_back_button)
        self.setLayout(input_layout)

        # define the experiment thread
        self.stop_event = threading.Event()
        self.finding_thread = FindMaxThread(
            self.moke, self.get_values, self.stop_event)
        self.finding_thread.finished.connect(self.found_maximum)

    def get_values(self):
        distance = float(self.max_dist_lineedit.text())
        start_step = float(self.start_step_lineedit.text())
        end_step = float(self.end_step_lineedit.text())
        return distance, start_step, end_step

    def found_maximum(self):
        self.start_button.setEnabled(True)
        self.go_back_button.setEnabled(True)

    def start(self):
        self.last_position = self.get_position()
        self.start_button.setEnabled(False)
        self.go_back_button.setEnabled(False)
        self.finding_thread.start()

    def get_position(self):
        return self.moke.instruments['stage'].get_position()

    def go_back(self):
        self.moke.instruments['stage'].set_position(self.last_position)

    def stop(self):
        if self.finding_thread.isRunning():
            self.stop_event.set()
            self.finding_thread.wait(0.1)


if __name__ == '__main__':
    # from control.instruments.moke import Moke

    # with Moke() as moke:
    #     app = QApplication(sys.argv)
    #     aw = FindMaxSignal(moke)
    #     aw.show()
    #     qApp.exec_()

    from unittest.mock import MagicMock
    moke = MagicMock()
    moke.instruments['stage'].get_position(return_value=[0, 0, 0, 0])
    app = QApplication(sys.argv)
    aw = FindMaxSignal(moke)
    aw.show()
    qApp.exec_()
