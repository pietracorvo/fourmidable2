import trimesh
import numpy as np

# load a file by name or from a buffer
struct = trimesh.load(r'C:\Users\user\Documents\Python\MOKEpy\display\Magnet.stl')
axes_struct = trimesh.load(r'C:\Users\user\Documents\Python\MOKEpy\display\right_hand_system_assembled.stl')
axes_struct.apply_transform(0.05*np.array(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))

phi = np.pi / 6
c, s = np.cos(phi), np.sin(phi)
R = np.array(((s, c, 0, 0), (-c, s, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
struct.apply_transform(R)

ax_swap = np.array(((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))
ax_swap2 = np.array(((0, 0, 1, 0), (0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))
axes_struct.apply_transform(ax_swap2.dot(ax_swap))

# -*- coding: utf-8 -*-
"""
Simple examples demonstrating the use of GLMeshItem.

"""

from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.opengl as gl

app = QtGui.QApplication([])
w = gl.GLViewWidget()
w.show()
w.setWindowTitle('pyqtgraph example: GLMeshItem')
w.setCameraPosition(distance=40)

g = gl.GLGridItem()
# g.scale(2, 2, 1)
g.rotate(90, 0, 1, 0)
g.translate(-20, 0, 0)
g1 = gl.GLGridItem()
# g1.scale(2, 2, 1)
w.addItem(g1)
w.addItem(g)

import numpy as np

## Mesh item will automatically compute face normals.
faces_darkness = 0.7
edge_darkness = 0.9

m1 = gl.GLMeshItem(vertexes=struct.vertices, faces=struct.faces,
                   color=(faces_darkness, faces_darkness, faces_darkness, 0.3), smooth=True,
                   edgeColor=(edge_darkness, edge_darkness, edge_darkness, 1), drawFaces=True, drawEdges=True,
                   shader='balloon')
ax_mesh = gl.GLMeshItem(vertexes=axes_struct.vertices, faces=axes_struct.faces,
                        color=(faces_darkness, faces_darkness, faces_darkness, 0.3), smooth=True,
                        edgeColor=(edge_darkness, edge_darkness, edge_darkness, 1), drawFaces=True, drawEdges=True,
                        shader='balloon')

m1.setGLOptions('additive')
w.addItem(m1)
w.addItem(ax_mesh)

ax = gl.GLAxisItem()
ax.setSize(x=10, y=10, z=10)
w.addItem(ax)

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
