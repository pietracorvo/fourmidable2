from PyQt5 import QtCore
from PyQt5.QtWidgets import *
import pyqtgraph.opengl as gl
from pyqtgraph.dockarea import DockArea

from display.instrument_plotting import *
import trimesh

# pg.setConfigOption('background', 'w')
# # pg.setConfigOption('background', (239, 239, 239))
# pg.setConfigOption('foreground', 'k')


class DynamicInstrumentPlot(QWidget):
    """A canvas that updates itself at a given framerate with a new plot."""

    def __init__(self, instrument_view, instrument_plot, framerate=20, autostart=False, timer=None):
        QWidget.__init__(self)
        self.instrument_view = instrument_view
        self.instrument_plot = instrument_plot

        layout = QHBoxLayout()
        layout.addWidget(self.instrument_view)
        self.setLayout(layout)

        if timer is None:
            self.timer = QtCore.QTimer(self)
        else:
            self.timer = timer
        self.timer.timeout.connect(self.update_plot)

        self.framerate = framerate
        if autostart:
            self.start()

    def start(self):
        self.timer.start(1000 / self.framerate)

    def update_plot(self):
        self.instrument_plot.plot()

class DynamicHPPlot(DynamicInstrumentPlot):
    def __init__(self, inst, framerate=20, timer=None, autostart=False):
        self.view = gl.GLViewWidget()
        self.view.opts['distance'] = 40
        # self.view.setBackgroundColor(pg.mkColor('w'))
        self.view.show()
        # load a file by name or from a buffer
        struct = trimesh.load(r'C:\Users\user\Documents\Python\MOKEpy\display\Magnet.stl')
        phi = np.pi / 6
        axes_struct = trimesh.load(r'C:\Users\user\Documents\Python\MOKEpy\display\right_hand_system_assembled.stl')
        axes_struct.apply_transform(0.05 * np.array(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))))
        c, s = np.cos(phi), np.sin(phi)
        R = np.array(((s, c, 0, 0), (-c, s, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
        struct.apply_transform(R)
        ax_swap = np.array(((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1)))
        ax_swap2 = np.array(((0, 0, 1, 0), (0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))
        axes_struct.apply_transform(ax_swap2.dot(ax_swap))

        g = gl.GLGridItem()
        g.scale(0.5, 0.5, 0.5)
        g.rotate(90, 0, 1, 0)
        g1 = gl.GLGridItem()
        self.view.addItem(g1)
        self.view.addItem(g)


        faces_darkness = 0.7
        edge_darkness = 0.9

        face_colors = np.array(struct.visual.face_colors) / 255
        vertex_colors = np.array(struct.visual.vertex_colors) / 255
        meshdata = gl.MeshData(vertexes=struct.vertices, faces=struct.faces, edges=struct.edges,
                               faceColors=face_colors,
                               vertexColors=vertex_colors)
        mesh = gl.GLMeshItem(meshdata=meshdata, drawFaces=True, drawEdges=False, shader="edgeHilight", smooth=True,
                             glOptions="opaque")

        ax_mesh = gl.GLMeshItem(vertexes=axes_struct.vertices, faces=axes_struct.faces,
                                color=(faces_darkness, faces_darkness, faces_darkness, 0.3), smooth=True,
                                edgeColor=(edge_darkness, edge_darkness, edge_darkness, 1), drawFaces=True,
                                drawEdges=True,
                                shader='edgeHilight')

        self.view.addItem(ax_mesh)
        self.view.addItem(mesh)

        # add axes
        ax = gl.GLAxisItem()
        ax.setSize(x=10, y=10, z=10)
        self.view.addItem(ax)

        self.plt = gl.GLLinePlotItem()
        self.view.addItem(self.plt)

        self.inst_plot = HPplotting(inst, self.plt)
        DynamicInstrumentPlot.__init__(
            self, self.view, self.inst_plot, framerate, autostart=True, timer=timer)

class CameraWidget(QWidget):
    """A canvas that updates itself at a given framerate with a new plot."""
    def __init__(self, instrument_view, instrument_plot, framerate=20):
        QWidget.__init__(self)
        self.instrument_view = instrument_view
        self.instrument_plot = instrument_plot

        layout = QHBoxLayout()
        layout.addWidget(self.instrument_view)
        self.setLayout(layout)
        self.framerate = framerate

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.start()

    def start(self):
        self.timer.start(1000 / self.framerate)

    def update_plot(self):
        self.instrument_plot.plot()


class DynamicCameraPlot(CameraWidget):
    def __init__(self, cam, framerate=20):
        self.view = pg.GraphicsView()
        self.viewbox = pg.ViewBox()
        self.viewbox.setAspectLocked(True)
        self.plt = pg.ImageItem(border='w')
        self.viewbox.addItem(self.plt)
        self.view.setCentralItem(self.viewbox)

        self.camera_plot = CameraPlotting(cam, plt=self.plt, view=self.viewbox)
        super().__init__(self.view, self.camera_plot, framerate)


class DynamicMokePlot(DynamicInstrumentPlot):
    def __init__(self, moke, framerate=20):
        self.view = pg.GraphicsView()
        layout = pg.GraphicsLayout()
        self.view.setCentralItem(layout)

        self.moke_plot = MokePlotting(moke, layout)

        DynamicInstrumentPlot.__init__(
            self, self.view, self.moke_plot, framerate=framerate, autostart=True)
