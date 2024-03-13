import numpy as np
import pandas as pd
from ..instrument import Instrument
from control.controllers import *


class Smaract(Instrument):
    """Class defining motors of the Newport controller

        The class inherits Instrument class.

        Args:
            motor (str, list of str): Defines the motors on the Newport controller
    """

    def __init__(self, controller, axes=None, velocity=None, **kwargs):
        """Sets the properties.

        Args:
            controller: SmaractControl controller class defined in the controllers
            motors: list of str containing the name of the axes. If None, numbers 0, ..., n_axes is used
            velocity: list or int velocity of movement of the axes. Can be an integer in pm/s or a list of instruments, one per axis. If None, default velocity is used.
            kwargs: keyword arguments of the Instrument class
        """
        assert isinstance(
            controller, SmaractControl), "Wrong controller passed!"
        Instrument.__init__(self, controller=controller, **kwargs)

        if axes is None:
            # use all the channels
            self.n_channels = self.controller.n_channels
            axes = {str(i): i for i in range(self.n_channels)}
        else:
            self.n_channels = len(axes)
        # axes needs to be a dict or None
        assert isinstance(axes, dict)
        self.axes = axes
        # axes values needs to be integers
        for ax in self.axes:
            assert isinstance(self.axes[ax], int)

        # set the velocity of the axes
        if velocity is not None:
            self.set_velocity(velocity)

        self.direction_labels = list(self.axes)

    def set_position(self, position, relative=False, wait=False):
        """Moves the axes to the given position after calibration. Position can be either the list with one value per axis, or a dictionary with axis name:value"""
        assert isinstance(position, list) or isinstance(
            position, dict) or isinstance(position, np.ndarray)
        # if list associate every direcion with one label
        if isinstance(position, list) or isinstance(position, np.ndarray):
            position = {lbl: pos for lbl, pos in zip(
                self.direction_labels, position)}
        # if position, assume one value per axis
        for ps in position:
            assert ps in self.direction_labels
        # fill in the missing axes
        current_position = self.get_position()
        position_all = dict()
        for ax, cpos in zip(self.direction_labels, current_position):
            if ax not in position:
                position_all[ax] = cpos
            elif relative:
                position_all[ax] = position[ax] + cpos
            else:
                position_all[ax] = position[ax]
        position_all = list(position_all.values())

        """The data2inst function applies the eucentric correction rotation+translation"""
        raw_position = self.calibration.data2inst(position_all)
        for ax, pos in zip(self.axes.values(), raw_position):
            self.controller.set_position(ax, pos, wait=wait)

    def set_velocity(self, velocity):
        """Sets the velocity of the axes"""
        if isinstance(velocity, int):
            velocity = [velocity] * self.n_channels
        # velocity can be None, int or list
        assert isinstance(velocity, list) or isinstance(velocity, np.ndarray)
        for ax, s in zip(self.axes.values(), velocity):
            self.controller.set_velocity(ax, s)

    def get_velocity(self):
        velocity = []
        for ax in self.axes.values():
            velocity.append(self.controller.get_velocity(ax))
        return velocity

    def set_acceleration(self, acceleration):
        """Sets the acceleration of the axes"""
        if isinstance(acceleration, int):
            acceleration = [acceleration] * self.n_channels
        # acceleration can be None, int or list
        assert isinstance(acceleration, list) or isinstance(acceleration, np.ndarray)
        for ax, s in zip(self.axes.values(), acceleration):
            self.controller.set_acceleration(ax, s)

    def get_acceleration(self):
        """"The default value is 0, meaning that the acceleration control is inactive"""
        acceleration = []
        for ax in self.axes.values():
            acceleration.append(self.controller.get_acceleration(ax))
        return acceleration

    def get_position(self):
        """Gets the current position of the motor after calibration"""
        # get the data from the controller
        raw_position = np.array([self.controller.get_position(
            ax) for ax in self.axes.values()])
        return self.calibration.inst2data(raw_position)

    def get_target(self):
        """Gets the current target position of the motor after calibration"""
        # get the data from the controller
        raw_target = np.array([self.controller.get_target(
            ax) for ax in self.axes.values()])
        return self.calibration.inst2data(raw_target)

    def get_data(self, *args, **kwargs):
        """Returns the data variable with the result of the get_position function"""
        return self.get_position(*args, **kwargs)

    def reference_axis(self, axis, reverse=False, velocity=5 * 10**8):
        self.controller.reference(
            self.axes[axis], reverse=reverse, velocity=velocity)

    def calibrate_axis(self, axis, reverse=False):
        self.controller.calibrate_channel(
            self.axes[axis], reverse=reverse)

    def is_referenced(self):
        return [self.controller.is_referenced(channel) for channel in self.axes.values()]

    def hold_position(self):
        """Actively holds the current position"""
        self.stop()
        current_position = self.get_position()
        self.set_position(current_position)

    def stop(self):
        self.controller.stop()

    def openStream(self, rate):
        self.controller.openStream(rate) #Stream base rate in Hz is needed to start

    def streamFrame(self, frameData):
        self.controller.streamFrame(frameData)

    def closeStream(self):
        self.controller.closeStream()

    def define_position(self, position):
        """Defines the current position"""
        assert isinstance(position, list) or isinstance(
            position, np.ndarray), "This should a be a list"
        raw_position = self.calibration.data2inst(position)
        for pos, channel in zip(raw_position, list(self.axes.values())):
            self.controller.define_position(channel, pos)

    def is_moving(self):
        for chn in self.axes.values():
            is_moving = self.controller.is_moving_channel(chn)
            if is_moving:
                return True
        return False


    def is_busy(self):
            return self.controller.is_busy()

    def rotate_position(self, position):
        """Defines the current position"""
        assert isinstance(position, list) or isinstance(
            position, np.ndarray), "This should a be a list"
        raw_position = self.calibration.data2inst(position)
        return raw_position