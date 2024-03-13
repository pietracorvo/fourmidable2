from control.controllers import *
from ..instrument import Instrument
import time


class PIStage(Instrument):
    """Class defining the PI rotation stage.

        The class inherits Instrument class. In general, there is no need for the calibration of this class since the
        device is pre-calibrated and the controller instructions are given in degrees.

        Args:
            velocity (num): Defines the velocity of the motor in degrees per second
            axis: The axis to use. In our case always 1 (as our PI device only has one axis)
    """

    def __init__(self, controller, velocity=5, **kwargs):
        """Sets the default parameters and references the axis.

        Args:
            controller: PI controller class defined in the controllers
            velocity: num velocity of the rotation in degrees per second
            kwargs: keyword arguments of the Instrument class
        """
        assert isinstance(controller, PIcontrol)
        Instrument.__init__(self, controller=controller, **kwargs)

        # define the axis to use
        self.axis = '1'
        # set servo on
        self.set_servo(1)
        # set referencing mode to 0
        self.controller.RON(self.axis, 0)
        # set velocity (in degrees per second)
        self.set_velocity(velocity)
        # # define the current position as 0
        # self.controller.POS(self.axis, 0)

    def set_servo(self, value):
        """Sets the servo of the controller to be either on (1) or off (0)"""
        assert value in {0, 1}
        self.controller.SVO(self.axis, value)

    def get_velocity(self):
        return self.calibration.inst2data(self.controller.qVEL()[self.axis])

    def set_velocity(self, value):
        # set velocity (in degrees per second)
        self.controller.VEL(self.axis, value)

    def set_position(self, position, relative=False, wait=False):
        """Moves the stage to the required position"""
        if relative:
            self.controller.MVR(
                self.axis, self.calibration.data2inst(position))
        else:
            self.controller.MOV(
                self.axis, self.calibration.data2inst(position))
        if wait:
            self.wait()

    def wait(self):
        while self.is_moving():
            time.sleep(0.1)

    def define_current_position(self, position):
        """Defines the current position"""
        self.controller.POS(self.axis, self.calibration.data2inst(position))

    def stop(self):
        """Stops all motion"""
        try:
            self.controller.STP()
        except:
            pass

    def get_position(self):
        """Gets the position of stage"""
        return self.calibration.inst2data(self.controller.qPOS()[self.axis])

    def get_target(self):
        """Gets the target position of stage"""
        return self.calibration.inst2data(self.controller.qMOV()[self.axis])

    def get_servo(self):
        """Gets the state of the servo (defines if the instrument is in the closed or open loop mode)"""
        return self.controller.qSVO()[self.axis]

    def is_moving(self):
        """Gets bool saying if the stage is moving"""
        return self.controller.IsMoving()[self.axis]

    def reference(self):
        """References the axis. It sets the rotator to known position 0.

        Careful as it might rotate almost 360degrees before finding it!
        """
        # references the axes
        self.controller.FRF(self.axis)
        # define the current position as 0
        self.controller.POS(self.axis, 0)
        # need to check, maybe have to put svo to 1 here

    def get_data(self, *args, **kwargs):
        """Returns the data variable with the result of the get_position function"""
        return self.get_position(*args, **kwargs)
