from control.controllers import *
from ..instrument import Instrument
from time import time


class CameraQuantalux(Instrument):

    def __init__(self, controller, **kwargs):
        Instrument.__init__(self, controller=controller, **kwargs)
        self.camera = controller.camera
        self._time_last_frame_sent = time()
        self._last_framerate_measured = None
        # self.exposure_time_ms = 1500

    @property
    def current_framerate(self):
        return self._last_framerate_measured

    @property
    def exposure_time_range_ms(self):
        return [e*0.001 for e in self.camera.exposure_time_range_us]

    @property
    def exposure_time_ms(self):
        return self.camera.exposure_time_us*0.001

    @property
    def sensor_width_pixels(self):
        return self.camera.sensor_width_pixels

    @property
    def sensor_height_pixels(self):
        return self.camera.sensor_height_pixels

    @property
    def binning(self):
        return (self.camera.binx, self.camera.biny)

    @exposure_time_ms.setter
    def exposure_time_ms(self, val):
        self.camera.exposure_time_us = int(val*1000)

    def get_data(self):
        while True:
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None:
                self.last_frame = frame.image_buffer
                self._update_framerate()
                return frame.image_buffer
            else:
                return self.last_frame

    def set_roi(self, upperleft_x, upperleft_y, lowerright_x, lowerright_y):
        # NOTE I have to disarm when changing roi
        self.camera.disarm()
        self.camera.roi = ROI(upperleft_x, upperleft_y, lowerright_x, lowerright_y)
        self.camera.arm(2)
        self.camera.issue_software_trigger()

    def set_binning(self, binning_tuple):
        self.camera.disarm()
        self.camera.binx = binning_tuple[0]
        self.camera.biny = binning_tuple[1]
        self.camera.arm(2)
        self.camera.issue_software_trigger()

    def get_roi(self):
        return self.camera.roi

    def reset_roi_if_roi_selected(self):
        if (self.camera.sensor_width_pixels != self.camera.image_width_pixels or
                self.camera.sensor_height_pixels != self.camera.image_height_pixels):
            self.set_roi(0, 0, self.camera.sensor_width_pixels, self.camera.sensor_height_pixels)

    def _update_framerate(self):
        new_time = time()
        try:
            fps = 1/(new_time-self._time_last_frame_sent)
        except ZeroDivisionError:
            fps = None
        self._time_last_frame_sent = new_time
        self._last_framerate_measured = fps
