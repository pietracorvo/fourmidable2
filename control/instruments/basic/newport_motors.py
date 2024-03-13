import numpy as np
import pandas as pd
from ..instrument import Instrument
from control.controllers import *


class NewportMotors(Instrument):
    """Class defining motors of the Newport controller

        The class inherits Instrument class.

        Args:
            motor (str, list of str): Defines the motors on the Newport controller
    """

    def __init__(self, controller, motors, velocity=1, max_speed=2000, **kwargs):
        """Sets the default properties.

        Args:
            controller: Newport controller class defined in the controllers
            motors: str or list of str containing the number of motor in question. E.g. '1' for motor 1 or ['1', '2']
            for motors '1' and '2'
            kwargs: keyword arguments of the Instrument class
        """
        assert isinstance(
            controller, NewportControl), "Wrong controller passed!"
        Instrument.__init__(self, controller=controller, **kwargs)

        if isinstance(motors, int):
            motors = [motors]
        self.motors = motors

        # set the maximum speed
        self.max_speed = max_speed
        self.set_velocity(velocity)
        self.direction_labels = list(self.motors.values())

    def set_position(self, position, relative=False, wait=False):
        """Moves the motor to the given position after calibration"""
        if len(self.motors) == 1 and not isinstance(position, list):
            position = [position]
        assert len(position) == len(
            self.motors), "Position needs to have as many parameters as there are motors"

        true_position = self.calibration.data2inst(position)

        # print('Set position: ', np.array(self.get_position())-np.array(position))
        for m, p in zip(self.motors, true_position):
            self.controller.set_position(p, m, relative=relative)
        if wait:
            self.controller.wait()

    def set_velocity(self, vel, wait=False):
        """Sets the velocity of the motor after calibration"""
        if not isinstance(vel, list):
            # not iterable
            vel = [vel] * len(self.motors)
        assert len(vel) == len(
            self.motors), "Velocity needs to have as many parameters as there are motors"

        true_velocity = [v * self.max_speed for v in vel]
        for m, v in zip(self.motors, true_velocity):
            self.controller.set_velocity(v, m)
        if wait:
            self.controller.wait()

    def get_position(self):
        """Gets the current position of the motor after calibration"""
        # get the data from the controller
        raw_position = [self.controller.get_position(m) for m in self.motors]
        return self.calibration.inst2data(raw_position)

    def get_target(self):
        """Gets the target position"""
        raw_position = [self.controller.get_target(m) for m in self.motors]
        return self.calibration.inst2data(raw_position)

    def get_velocity(self):
        """Gets the velocity of the motor after calibration"""
        raw_vel = [self.controller.get_velocity(m) for m in self.motors]
        vel = [v / self.max_speed for v in raw_vel]
        return vel

    def get_data(self, *args, **kwargs):
        """Returns the data variable with the result of the get_position function"""
        return self.get_position(*args, **kwargs)

    def time_to_position(self, position, relative=False):
        """Calculates the time required to travel to the given position in seconds"""
        raw_position = self.calibration.data2inst(position)
        # get the time for each of the axis
        time_per_axis = [self.controller.time_to_position(p, m, relative)
                         for p, m in zip(raw_position, self.motors)]
        return np.sum(time_per_axis)

    def stop(self):
        self.controller.stop()

    def define_current_position(self, position, wait=True):
        """Defines the current position"""
        if len(self.motors) == 1 and not isinstance(position, list):
            position = [position]
        assert len(position) == len(
            self.motors), "Position needs to have as many parameters as there are motors"

        true_position = self.calibration.data2inst(position)
        for m, p in zip(self.motors, true_position):
            self.controller.define_current_position(p, m)
        if wait:
            self.controller.wait()

    def create_save_group(self, group, name=None, additional=None):
        inst_group = super().create_save_group(group, name, additional)
        if isinstance(self.motors, dict):
            inst_group.attrs['motors'] = np.array([[key.encode('utf8'), value.encode('utf8')]
                                                   for key, value in self.motors.items()])
        else:
            inst_group.attrs['motors'] = np.array(
                [p.encode('utf8') for p in self.motors])
        return inst_group

    def save_data(self, group, data):
        # get the columns for the data
        if isinstance(self.motors, dict):
            columns = list(self.motors.values())
        else:
            columns = list(self.motors)
        # get the data
        data_pd = pd.DataFrame(np.array(data)[None, :], columns=columns)
        # save the data
        with pd.HDFStore(group.file.filename) as store:
            store.append(group.name + '/data', data_pd, data_columns=True)
        return group

    def is_moving(self):
        return self.controller.is_busy()
