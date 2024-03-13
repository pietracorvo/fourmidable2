from control.controllers import *
from ..instrument import Instrument
from instrumental import u


class Camera(Instrument):
    """Class defining the Thorlabs camera instrument.

        The class inherits Instrument class. Calibration here is a function which processes every image before it is
        output. It takes the acquired image and any additional calib_params

        Args:
            framerate (num): frame rate of live acquisition
            is_live (bool): flag to know if the live acquisition is on or off
    """

    def __init__(self, controller, framerate=25, exposure_time=0.04, start_live=True, hsub=1, vsub=1, **kwargs):
        """Sets the default parameters.

        Args:
            controller: Camera controller class defined in the controllers
            framerate: Specifies the frame rate of live acquisition. Default 25. If the frame rate is changed during
            live acquisition the acquisition is stopped and immediately continued with the new frame rate
        """
        Instrument.__init__(self, controller=controller, **kwargs)
        self.is_live = False
        self._framerate = framerate
        self.exposure_time = exposure_time
        self.hsub = hsub
        self.vsub = vsub
        if start_live:
            self.start_live()

    @property
    def framerate(self):
        return self._framerate

    @framerate.setter
    def framerate(self, value):
        self._framerate = value
        if self.is_live:
            self.stop()
            self._framerate = value
            self.start_live()
        else:
            self._framerate = value

    def grab_image(self):
        """Gets the latest image if we are in live video mode or takes a new image otherwise.
        Returns the image after calibration. """
        if self.is_live:
            img = self.controller.latest_frame()
        else:
            print('not live')
            img = self.controller.grab_image(
                exposure_time=self.exposure_time * u.s)
        return self.calibration.inst2data(img)

    def start_live(self):
        """Starts the live video"""
        self.controller.start_live_video(framerate="{} hertz".format(
            self.framerate), exposure_time=self.exposure_time * u.s, hsub=self.hsub, vsub=self.vsub)
        self.is_live = True

    def stop(self):
        """Stops the live video"""
        self.controller.stop_live_video()
        self.is_live = False

    def get_data(self):
        """Updates the data with the result from the grab_image function"""
        return self.grab_image()

    def save_data(self, group, data):
        if data is not None:
            dset = group.create_dataset('data', data=data)
            dset.attrs['CLASS'] = np.string_('IMAGE')
            dset.attrs['IMAGE_SUBCLASS'] = np.string_('IMAGE_TRUECOLOR')
            dset.attrs['TIME_TAKEN'] = np.string_(
                time.strftime("%Y%m%d-%H%M%S"))
