from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.widgets.RemoteGraphicsView
import numpy as np
from PyQt5.QtWidgets import *
import time

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Main window")
        self.main_widget = QWidget(self)

        self.plot_widget = App()
        layout = QHBoxLayout(self.main_widget)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self.setCentralWidget(self.main_widget)


class App(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.m = PlotCanvas(self)
        self.m2 = ImageCanvas(self)


        layout = QHBoxLayout()
        layout.addWidget(self.m.remote_view)
        layout.addWidget(self.m2)
        self.setLayout(layout)
        print('done')


class PlotCanvas():
    def __init__(self, parent):
        super().__init__()
        self.remote_view = pg.widgets.RemoteGraphicsView.RemoteGraphicsView()
        self.remote_view.pg.setConfigOptions(antialias=True)
        self.remote_view.setWindowTitle('pyqtgraph example: RemoteSpeedTest')
        self.layout = self.remote_view.pg.GraphicsLayout()
        self.plt = self.remote_view.pg.PlotItem()
        self.layout.addItem(self.plt)
        self.plt2 = self.layout.addPlot()
        self.plt._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
        self.plt2._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
        self.remote_view.setCentralItem(self.layout)

        self.parent = parent

        self.timer = QtCore.QTimer(self.parent)
        self.timer.timeout.connect(self.update_plot)
        print('starting')
        self.timer.start(50)

    def update_plot(self):
        data1 = np.random.normal(size=(10000, 50)).sum(axis=1)
        data1 += 5 * np.sin(np.linspace(0, 10, data1.shape[0]))
        data2 = np.random.normal(size=(10000, 50)).sum(axis=1)
        data2 += 5 * np.sin(np.linspace(0, 10, data2.shape[0]))
        data2 += 10
        self.plt.plot(data1, pen=(255,0,0), name="Red curve", clear=True, _callSync='off')
        self.plt2.plot(data2, pen=(0, 255,0), name="Green curve", clear=True, _callSync='off')

class ImageCanvas(pg.widgets.RemoteGraphicsView.RemoteGraphicsView):
    def __init__(self, parent):
        super().__init__()
        self.pg.setConfigOptions(antialias=True)
        self.setWindowTitle('pyqtgraph example: RemoteSpeedTest')
        self.view = self.pg.ViewBox()
        self.view.setAspectLocked(True)
        self.plt = self.pg.ImageItem(border='w')
        self.view.addItem(self.plt)
        self.plt._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
        self.setCentralItem(self.view)

        self.parent = parent

        self.timer = QtCore.QTimer(self.parent)
        self.timer.timeout.connect(self.update_plot)
        print('starting')
        self.timer.start(50)

    def update_plot(self):
        t0 = time.time()
    ## Create random image
        data = np.random.normal(size=(1024, 1280), loc=1024, scale=64).astype(np.uint16)
        self.plt.setImage(data, _callSync='off')
        print(time.time()-t0)

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    aw = MainWindow()
    aw.show()
    qApp.exec_()
    # app = QApplication(sys.argv)
    # aw = App(app)
    # # aw.main_app.show()
    # qApp.exec_()
