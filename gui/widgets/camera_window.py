import sys

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
import numpy as np
from gui.widgets.canvas import DynamicCameraPlot

class CameraWindow(QMainWindow):
    def __init__(self, camera, framerate=25):
        QMainWindow.__init__(self)
        self.camera = camera

        self.main_widget = QWidget(self)

        self.setCentralWidget(self.main_widget)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Camera")
        # set window size
        screen_size = QDesktopWidget().screenGeometry(-1)
        wanted_size = int(3 / 4 * np.min([screen_size.width(), screen_size.height()]))
        self.resize(wanted_size, wanted_size)

        self.camera_view = DynamicCameraPlot(self.camera)

        layout = QHBoxLayout(self.main_widget)
        # self.camera_canvas.setMinimumSize(200, 200)

        layout.addWidget(self.camera_view)
        self.setLayout(layout)

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()



if __name__ == '__main__':
    app = QApplication(sys.argv)

    from control.controllers import CameraControl
    from control.instruments.basic import Camera

    cc = CameraControl()
    cam = Camera(cc)
    aw = CameraWindow(cam)
    aw.show()
    qApp.exec_()
