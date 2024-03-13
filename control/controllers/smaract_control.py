import numpy as np
from warnings import warn
import smaract.ctl as ctl


class SmaractControl:
    def __init__(self, locator, name='', velocity=0):
        self.name = name
        # get a handle to the device
        self.d_handle = ctl.Open(locator)
        global sm_handle
        sm_handle = self.d_handle
        # get the number of channel
        n_channels_tot = ctl.GetProperty_i32(
            self.d_handle, 0, ctl.Property.NUMBER_OF_CHANNELS)
        is_active = [ctl.GetProperty_i32(self.d_handle, channel, ctl.Property.CHANNEL_STATE)
                     & ctl.ChannelState.SENSOR_PRESENT != 0 for channel in range(n_channels_tot)]
        self.n_channels = np.sum(is_active)
        self.channels = np.array(is_active).nonzero()[0]
        # get the channel type in terms of the base unit (meter or degree)
        self.base_units = [ctl.GetProperty_i32(
            self.d_handle, channel, ctl.Property.POS_BASE_UNIT) for channel in self.channels]
        if velocity is not None:
            if isinstance(velocity, list):
                for channel, v in zip(self.channels, velocity):
                    self.set_velocity(v, channel)
            else:
                for channel in self.channels:
                    self.set_velocity(channel, velocity)

        # set all channels to absolute move mode and infinite hold time
        for channel in self.channels:
            ctl.SetProperty_i32(self.d_handle, channel,
                                ctl.Property.MOVE_MODE, ctl.MoveMode.CL_ABSOLUTE)
            ctl.SetProperty_i32(self.d_handle, channel,
                                ctl.Property.HOLD_TIME, ctl.HOLD_TIME_INFINITE)

    def set_position(self, channel, position, relative=False, wait=False):
        """Queues the motor movement to the given position"""
        if relative:
            move_mode = ctl.MoveMode.CL_RELATIVE
        else:
            move_mode = ctl.MoveMode.CL_ABSOLUTE

        # # maybe setting this method every time is not necessary and would be quicker to get the state and only change it if requested
        ctl.SetProperty_i32(self.d_handle, channel,
                            ctl.Property.MOVE_MODE, move_mode)
        ctl.Move(self.d_handle, channel, int(position), 0)
        if wait:
            self.wait()
    #
    def set_velocity(self, channel, velocity):
        """Sets the velocity to velocity pm/s"""
        # Set move velocity [in pm/s].
        ctl.SetProperty_i64(self.d_handle, channel,
                            ctl.Property.MOVE_VELOCITY, int(velocity))

    def get_velocity(self, channel):
        """Gets the velocity in pm/s"""
        # Set move velocity [in pm/s].
        return ctl.GetProperty_i64(self.d_handle, channel,
                                   ctl.Property.MOVE_VELOCITY)

    def set_acceleration(self, channel, acceleration):
        """Sets the acceleration to velocity pm/s^2"""
        # Set move acceleration [in pm/s^2].
        ctl.SetProperty_i64(self.d_handle, channel,
                            ctl.Property.MOVE_ACCELERATION, int(acceleration))

    def get_acceleration(self, channel):
        """Gets the acceleration in pm/s^2"""
        # Set move acceleration [in pm/s^2].
        return ctl.GetProperty_i64(self.d_handle, channel,
                                   ctl.Property.MOVE_ACCELERATION)

    def get_position(self, channel):
        """Gets the current position of the axis before any calibration"""
        try:
            position = ctl.GetProperty_i64(
                self.d_handle, channel, ctl.Property.POSITION)
        except:
            position = 0
            warn('Could not get position')

        return position

    def get_target(self, channel):
        """Gets the current position of the axis before any calibration"""
        target = ctl.GetProperty_i64(
            self.d_handle, channel, ctl.Property.TARGET_POSITION)
        return target

    def stop_channel(self, channel):
        try:
            ctl.Stop(self.d_handle, channel)
        except:
            print('Channel {} does not want to stop!!!'.format(channel))

    def stop(self):
        for channel in self.channels:
            self.stop_channel(channel)

    def calibrate(self, reverse=False):
        for channel in self.channels:
            self.calibrate_channel(channel, reverse=reverse)

    def calibrate_channel(self, channel, reverse=False):
        # Set calibration options (start direction: forward)
        ref_dir = 1 if reverse else 0
        ctl.SetProperty_i32(self.d_handle, channel,
                            ctl.Property.CALIBRATION_OPTIONS, ref_dir)
        # Start calibration sequence
        ctl.Calibrate(self.d_handle, channel)

    def define_position(self, channel, position):
        ctl.SetProperty_i64(self.d_handle, channel,
                            ctl.Property.POSITION, int(position))

    def wait(self, timeout=None):
        """Waits for the event from the controller"""
        if timeout is None:
            event = ctl.WaitForEvent(self.d_handle, ctl.INFINITE)
        else:
            event = ctl.WaitForEvent(self.d_handle, timeout)
        # print(ctl.GetEventInfo(event))

    def close_connection(self):
        try:
            ctl.Close(self.d_handle)
        except:
            print('Smaract connection already closed.')

    def is_moving_channel(self, channel):
        state = ctl.GetProperty_i32(
            self.d_handle, 0, ctl.Property.CHANNEL_STATE)
        is_moving = (state & ctl.ChannelState.ACTIVELY_MOVING) != 0
        return is_moving

    def is_moving(self):
        for channel in self.channels:
            state = ctl.GetProperty_i32(
                self.d_handle, 0, ctl.Property.CHANNEL_STATE)
            is_moving = (state & ctl.ChannelState.ACTIVELY_MOVING) != 0
            if is_moving:
                return True
        return False

    def is_busy(self):
        for channel in self.channels:
            state = ctl.GetProperty_i32(
                self.d_handle, 0, ctl.Property.CHANNEL_STATE)
            is_moving = (state & ctl.ChannelState.IS_STREAMING) != 0
            if is_moving:
                return True
        return False

    def reference(self, channel, velocity=5 * 10**8, reverse=False):
        initial_velocity = self.get_velocity(channel)
        ctl.SetProperty_i64(self.d_handle, channel,
                            ctl.Property.MOVE_VELOCITY, 5 * 10**8)
        if reverse:
            ref_options = ctl.ReferencingOption.REVERSE_DIR | ctl.ReferencingOption.STOP_ON_REF_FOUND
        else:
            ref_options = ctl.ReferencingOption.START_DIR | ctl.ReferencingOption.STOP_ON_REF_FOUND
        ctl.SetProperty_i32(self.d_handle, channel,
                            ctl.Property.REFERENCING_OPTIONS, ref_options)
        ctl.Reference(self.d_handle, channel)
        self.set_velocity(channel, initial_velocity)

    def is_referenced(self, channel):
        state = ctl.GetProperty_i32(
            self.d_handle, channel, ctl.Property.CHANNEL_STATE)
        is_referenced = (state & ctl.ChannelState.IS_REFERENCED) != 0
        return is_referenced

    def openStream(self, rate):
        ctl.SetProperty_i32(self.d_handle, 0, ctl.Property.STREAM_BASE_RATE, rate)
        self.s_handle = ctl.OpenStream(self.d_handle)

    def closeStream(self):
        ctl.CloseStream(self.d_handle, self.s_handle)

    def streamFrame(self, frameData):
        ctl.StreamFrame(self.d_handle, self.s_handle, frameData)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.is_moving():
            self.stop()
        self.close_connection()


def list_usbs():
    """Prints the list of smaract devices connected"""
    buffer = ctl.FindDevices()
    if len(buffer) == 0:
        print("MCS2 no devices found.")
        exit(1)
    locators = buffer.split("\n")
    for locator in locators:
        print("MCS2 available devices: {}".format(locator))
