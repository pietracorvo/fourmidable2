# -*- coding: utf-8 -*-
"""
Demonstrate use of GLLinePlotItem to draw cross-sections of a surface.

"""
# Add path to library (just for examples; you do not need this)
# import initExample
import trimesh

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np

app = QtGui.QApplication([])
win = QtGui.QMainWindow()
view = gl.GLViewWidget()
view.opts['distance'] = 40
struct = trimesh.load(r'C:\Users\user\Documents\Python\MOKEpy\display\Magnet.stl')

faces_darkness = 0.7
edge_darkness = 0.9
face_colors = np.array(struct.visual.face_colors)/255
# face_colors[:, :-1] = 1
# face_colors[:, -1] = 1
vertex_colors=np.array(struct.visual.vertex_colors) / 255
meshdata = gl.MeshData(vertexes=struct.vertices, faces=struct.faces, edges=struct.edges,
                       faceColors=face_colors,
                       vertexColors=vertex_colors)
mesh = gl.GLMeshItem(meshdata=meshdata, drawFaces=True, drawEdges=False, shader="edgeHilight", smooth=True, glOptions="opaque")

view.addItem(mesh)

win.setCentralWidget(view)
win.resize(800, 800)
win.show()

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
