import sys
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import numpy as np
import warnings

from experiments.basic import zero_magnet
from experiments.take_field_steps import take_steps
import threading


class ApplySteps(QWidget):

    def __init__(self, moke):
        super().__init__()
        self.setWindowTitle('Apply step loop')

        self.moke = moke

        # add apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_button_clicked)
        # add stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_fields)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.stop_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)


    def stop_fields(self):
        try:
            self.tune_stop.set()
        except AttributeError:
            pass
        zero_magnet(self.moke)
        print('Zeroed the magnet')

    def apply_button_clicked(self):

        signals = [[2, 0, 0],
                   [4, 0, 0],
                   [6, 0, 0],
                   [8, 0, 0],
                   # [6, 0, 0],
                   # [4, 0, 0],
                   # [2, 0, 0],
                   # [0, 0, 0],
                   ]
        self.tune_stop = threading.Event()
        take_steps(self.moke, signals, self.tune_stop)


if __name__ == '__main__':
    qApp = QApplication(sys.argv)
    aw = ApplySteps(1)

    aw.show()
    qApp.exec_()
