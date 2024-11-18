import sys
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
#from PyQt5.QtWidgets import QSizePolicy
import numpy as np


class CameraHamamatsuSettings(QWidget):

    def __init__(self, moke):
        super().__init__()
        self.cam = moke.instruments['hamamatsu_camera']
        self.setWindowTitle('Camera settings for Hamamatsu')

        self.input_exposuretime = QDoubleSpinBox()  # in micro seconds
        self.input_exposuretime.setMinimum(self.cam.exposure_time_range_ms[0])
        self.input_exposuretime.setMaximum(self.cam.exposure_time_range_ms[1])
        self.input_exposuretime.setValue(self.cam.exposure_time_ms)
        self.input_exposuretime.editingFinished.connect(self.change_camera_exposure_time)

        layout_1 = QGridLayout()
        layout_1.addWidget(QLabel('Exposure time [ms]'), 1, 1)
        layout_1.addWidget(self.input_exposuretime, 1, 2)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout_1)
        self.setLayout(main_layout)

    def change_camera_exposure_time(self):
        self.cam.exposure_time_ms = self.input_exposuretime.value()

if __name__ == '__main__':
    from control.instruments.moke import Moke

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = CameraHamamatsuSettings(moke)
        aw.show()
        qApp.exec_()
