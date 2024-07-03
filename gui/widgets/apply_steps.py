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

        # signals = np.zeros((500,3))

        amplitude = 15
        nb_steps = 120
        nb_cycles = 2

        # cycle = (np.linspace(amplitude, -amplitude, 2*nb_steps).tolist()
        #          + np.linspace(-amplitude, amplitude, 2*nb_steps).tolist()[1:])
        # sequence = np.linspace(0, amplitude, nb_steps).tolist() + 2 * cycle
        # signals = np.array([
        #     np.zeros(len(sequence)),
        #     np.zeros(len(sequence)),
        #     sequence,
        # ]).T

        amplitude = 15
        nb_steps = 60
        nb_cycles = 2
        seq = []
        for i in np.linspace(0, 2 * np.pi, nb_steps):
            #seq.append([amplitude*np.sin(i), 0., amplitude*np.cos(i)])
            seq.append([0., 0., amplitude * np.sin(i)])
        # seq = seq[:-1]
        seq *= nb_cycles
        # start = []
        # for i in np.linspace(0, amplitude, nb_steps):
        #     start.append([0., 0., i])
        # seq = start + seq
        signals = np.array(seq)

        # cycle = [7.5, 8., 8.5, 9., 9.5, 10., 10.5, 11., 11.5, 12, 13.5, 15.]
        # #cycle = np.linspace(0, 15, 40).tolist()
        # tmp = cycle[:-1].copy()
        # tmp.reverse()
        # cycle += tmp
        # cycle += [-x for x in cycle]
        # cycle *= 2
        # signals = np.array([
        #     np.zeros(len(cycle)),
        #     np.zeros(len(cycle)),
        #     cycle,
        # ]).T

        self.tune_stop = threading.Event()
        take_steps(self.moke, signals, self.tune_stop)


if __name__ == '__main__':
    qApp = QApplication(sys.argv)
    aw = ApplySteps(1)

    aw.show()
    qApp.exec_()
