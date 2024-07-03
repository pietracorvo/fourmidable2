from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, ROI
from thorlabs_tsi_sdk.tl_camera_enums import DATA_RATE
import os, sys


class CameraControllerQuantalux:

    def __init__(self, name):
        # Make Thorlabs DLLs available
        absolute_path_to_dlls = os.path.abspath('thorlabs_camera_DLLs')
        os.environ['PATH'] = absolute_path_to_dlls + os.pathsep + os.environ['PATH']
        os.add_dll_directory(absolute_path_to_dlls)

        try:
            # the sdk must be always alive during camera operation and there can only be one
            # instance of the sdk, which means currently you can have only one camera at the same time
            self._sdk = TLCameraSDK()
            camera_list = self._sdk.discover_available_cameras()
            self.camera = self._sdk.open_camera(camera_list[0])
            # apply start conditions for camera
            # NOTE set data_rate only supported for Quantalux not foir Kiralux
            #self.camera.data_rate = DATA_RATE.FPS_30   # or DATA_RATE.FPS_50 to run faster but with more noise
            self.camera.frames_per_trigger_zero_for_unlimited = 0
            self.camera.image_poll_timeout_ms = 0
            self.camera.roi = ROI(0, 0, self.camera.sensor_width_pixels, self.camera.sensor_height_pixels)
            self.camera.arm(2)
            self.camera.issue_software_trigger()
        except:
            print('Unable to open camera!')

    def __exit__(self, *args):
        try:
            self.camera.dispose()
        except:
            pass
