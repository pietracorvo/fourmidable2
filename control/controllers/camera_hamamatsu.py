from pylablib.devices import DCAM
import os


class CameraControllerHamamatsu:

    def __init__(self, name):
        # Make Thorlabs DLLs available

        try:
            self.camera = DCAM.DCAMCamera()
            self.camera.set_attribute_value("EXPOSURE TIME", 0.1)   # TODO seems not to work
        except:
            print('Unable to open camera!')

    def __exit__(self, *args):
        try:
            self.camera.close()
        except:
            pass
