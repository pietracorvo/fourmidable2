from control.controllers import *
from ..instrument import Instrument
from time import time


class CameraQuantalux(Instrument):

    def __init__(self, controller, **kwargs):
        Instrument.__init__(self, controller=controller, **kwargs)
        self.camera = controller.camera
        self._time_last_frame_sent = time()
        self._last_framerate_measured = None

    @property
    def current_framerate(self):
        return self._last_framerate_measured

    @property
    def exposure_time_range_us(self):
        return self.camera.exposure_time_range_us

    @property
    def exposure_time_us(self):
        return self.camera.exposure_time_us

    @exposure_time_us.setter
    def exposure_time_us(self, val):
        self.camera.exposure_time_us = val

    def get_data(self):
        # TODO for long exposure times the refresh rate of the main gui is slowed down here
        while True:
            frame = self.camera.get_pending_frame_or_null()
            if frame is not None:
                self._update_framerate()
                return frame.image_buffer

    def set_roi(self, upperleft_x, upperleft_y, lowerright_x, lowerright_y):
        # NOTE docs say i have to disarm when changing roi
        self.camera.disarm()
        self.camera.roi = ROI(upperleft_x, upperleft_y, lowerright_x, lowerright_y)
        self.camera.arm(2)
        self.camera.issue_software_trigger()

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


    # TODO stuff copied from istruments\basic\camera.py
    #      seems not to be needed for the moment, but should mabe be implemented at some point
    #
    # def __init__(self, controller, framerate=25, exposure_time=0.04, start_live=True, hsub=1, vsub=1, **kwargs):
    #     Instrument.__init__(self, controller=controller, **kwargs)
    #     self.is_live = False
    #     self._framerate = framerate
    #     self.exposure_time = exposure_time
    #     self.hsub = hsub
    #     self.vsub = vsub
    #     if start_live:
    #         self.start_live()
    #
    # @property
    # def framerate(self):
    #     return self._framerate
    #
    # @framerate.setter
    # def framerate(self, value):
    #     self._framerate = value
    #     if self.is_live:
    #         self.stop()
    #         self._framerate = value
    #         self.start_live()
    #     else:
    #         self._framerate = value
    #
    # def grab_image(self):
    #     """Gets the latest image if we are in live video mode or takes a new image otherwise.
    #     Returns the image after calibration. """
    #     if self.is_live:
    #         img = self.controller.latest_frame()
    #     else:
    #         print('not live')
    #         img = self.controller.grab_image(
    #             exposure_time=self.exposure_time * u.s)
    #     return self.calibration.inst2data(img)
    #
    # def start_live(self):
    #     """Starts the live video"""
    #     self.controller.start_live_video(framerate="{} hertz".format(
    #         self.framerate), exposure_time=self.exposure_time * u.s, hsub=self.hsub, vsub=self.vsub)
    #     self.is_live = True
    #
    # def stop(self):
    #     """Stops the live video"""
    #     self.controller.stop_live_video()
    #     self.is_live = False
    #
    # def get_data(self):
    #     """Updates the data with the result from the grab_image function"""
    #     return self.grab_image()
    #
    # def save_data(self, group, data):
    #     if data is not None:
    #         dset = group.create_dataset('data', data=data)
    #         dset.attrs['CLASS'] = np.string_('IMAGE')
    #         dset.attrs['IMAGE_SUBCLASS'] = np.string_('IMAGE_TRUECOLOR')
    #         dset.attrs['TIME_TAKEN'] = np.string_(
    #             time.strftime("%Y%m%d-%H%M%S"))
