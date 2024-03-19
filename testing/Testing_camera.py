from control.instruments.moke import Moke
from display.instrument_plotting import CameraPlotting
import matplotlib.pyplot as plt

mk = Moke()

cam = mk.instruments['camera1']

cam_plotting = CameraPlotting(cam)

cam_plotting.start_animation()

plt.show()

del mk