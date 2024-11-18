from control.controllers import *
from ..instrument import Instrument
from time import time

class CameraHamamatsu(Instrument):

    def __init__(self, controller, **kwargs):
        Instrument.__init__(self, controller=controller, **kwargs)
        self.camera = controller.camera
        self._time_last_frame_sent = time()
        self._last_framerate_measured = None
        self.exposure_time_ms = 3
        self.start_acquisition()
        self.last_frame = None  # gets initialized in next line
        _ = self.get_single_image()

    def start_acquisition(self):
        self.camera.setup_acquisition(mode='sequence', nframes=1)
        self.camera.start_acquisition()

    @property
    def current_framerate(self):
        return self._last_framerate_measured

    @property
    def exposure_time_range_ms(self):
        exp_attri = self.camera.get_attribute("exposure_time")
        return [1000 * exp_attri.min, 1000 * exp_attri.max]

    @property
    def exposure_time_ms(self):
        return self.camera.get_attribute_value("EXPOSURE TIME")*(1000)

    @property
    def sensor_width_pixels(self):
        return self.camera.get_attribute_value("image_width")

    @property
    def sensor_height_pixels(self):
        return self.camera.get_attribute_value("image_height")

    @property
    def binning(self):
        pass
        # return (self.camera.binx, self.camera.biny)

    @exposure_time_ms.setter
    def exposure_time_ms(self, val):
        self.camera.set_attribute_value("EXPOSURE TIME", val/1000)

    def get_data(self):
        """Used for the display camera image plot widget,
        does NOT BLOCK until new image acquired, just returns last image. """
        frame = self.camera.read_newest_image()
        if frame is not None:
            self.last_frame = frame
            self._update_framerate()
            return frame
        else:
            return self.last_frame

    def get_single_image(self):
        """Used in experiment, BLOCKS until a new image is acquired."""
        while True:
            frame = self.camera.grab(1)
            if frame is not None:
                self._update_framerate()
                self.last_frame = frame[0]
                return frame[0]

    def set_roi(self, upperleft_x, upperleft_y, lowerright_x, lowerright_y):
        pass
        # # NOTE I have to disarm when changing roi
        # self.camera.disarm()
        # self.camera.roi = ROI(upperleft_x, upperleft_y, lowerright_x, lowerright_y)
        # self.camera.arm(2)
        # self.camera.issue_software_trigger()

    def set_binning(self, binning_tuple):
        pass
        # self.camera.disarm()
        # self.camera.binx = binning_tuple[0]
        # self.camera.biny = binning_tuple[1]
        # self.camera.arm(2)
        # self.camera.issue_software_trigger()

    def get_roi(self):
        pass
        # return self.camera.roi

    def reset_roi_if_roi_selected(self):
        pass
        # if (self.camera.sensor_width_pixels != self.camera.image_width_pixels or
        #         self.camera.sensor_height_pixels != self.camera.image_height_pixels):
        #     self.set_roi(0, 0, self.camera.sensor_width_pixels, self.camera.sensor_height_pixels)

    def _update_framerate(self):
        new_time = time()
        try:
            fps = 1/(new_time-self._time_last_frame_sent)
        except ZeroDivisionError:
            fps = None
        self._time_last_frame_sent = new_time
        self._last_framerate_measured = fps