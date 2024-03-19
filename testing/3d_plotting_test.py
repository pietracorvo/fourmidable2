


# -*- coding: utf-8 -*-
"""
Demonstrate use of GLLinePlotItem to draw cross-sections of a surface.

"""
# Add path to library (just for examples; you do not need this)
# import initExample

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np

app = QtGui.QApplication([])
w = gl.GLViewWidget()
w.opts['distance'] = 40
w.show()
w.setWindowTitle('pyqtgraph example: GLLinePlotItem')

gx = gl.GLGridItem()
gx.rotate(90, 0, 1, 0)
gx.translate(-10, 0, 0)
w.addItem(gx)
gy = gl.GLGridItem()
gy.rotate(90, 1, 0, 0)
gy.translate(0, -10, 0)
w.addItem(gy)
gz = gl.GLGridItem()
gz.translate(0, 0, -10)
w.addItem(gz)


class live_plot:
    def __init__(self, w):
        self.amp = 10
        self.n = 100
        self.phi = np.linspace(0, 3*np.pi, self.n)

        self.color = np.ones([self.n, 4])
        self.color[:, 3] = np.linspace(0, 1, self.n)
        self.color[:, 0:3] = np.repeat(np.array([0.121, 0.465, 0.703])[None, :], self.n, axis=0)
        y = self.amp*np.sin(self.phi)
        x = np.zeros(y.shape)
        z = self.amp*np.cos(self.phi)
        pts = np.vstack([x, y, z]).transpose()
        self.plt = gl.GLLinePlotItem()
        w.addItem(self.plt)
        self.delta_phi = np.pi/10

        self.t = QtCore.QTimer()
        self.t.timeout.connect(self.update)
        self.t.start(50)

    def update(self):
        self.phi = np.linspace(
            self.phi[0]+self.delta_phi, self.phi[-1] + self.delta_phi, self.n)
        y = self.amp*np.sin(self.phi)
        x = np.zeros(y.shape)
        z = self.amp*np.cos(self.phi)
        pts = np.vstack([x, y, z]).transpose()
        self.plt.setData(pos=pts, width=1, color=self.color)


lp = live_plot(w)


# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
