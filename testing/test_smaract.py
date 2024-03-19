import unittest
import sys
import os

from instrumental.drivers.daq.ni import NIDAQ
sys.path.append('.')
from control.instruments.moke import Moke
from control.load_from_settings import read_settings
import smaract.ctl as ctl
import numpy as np
# import matplotlib.pyplot as plt


class NItimingTest(unittest.TestCase):

    def setUp(self):
        settings_data = read_settings()
        # only keep the smaract controllers
        settings_data['controllers'] = [
            cnt for cnt in settings_data['controllers'] if cnt["type"] in {"SmaractControl", }]
        # only keep the ni instruments
        settings_data['instruments'] = {
            "stage": settings_data["instruments"]['stage']}

    def test_smaract_connection(self):
        locator = ctl.FindDevices()
        d_handle = ctl.Open(locator)
        print('Found smaract on: ', locator)
        print('\nSmaract properties: \n')
        n_channels_tot = ctl.GetProperty_i32(
            d_handle, 0, ctl.Property.NUMBER_OF_CHANNELS)
        print('Total channels: ', n_channels_tot)
        n_channels = np.sum([ctl.GetProperty_i32(d_handle, channel, ctl.Property.CHANNEL_STATE) &
                             ctl.ChannelState.SENSOR_PRESENT != 0 for channel in range(n_channels_tot)])
        print('N channels in use: ', n_channels)
        base_units = [ctl.GetProperty_i32(
            d_handle, channel, ctl.Property.POS_BASE_UNIT) for channel in range(n_channels)]
        print('Base units: ', ['pm' if bu
                               == ctl.BaseUnit.METER else 'deg' for bu in base_units])
        positions = [ctl.GetProperty_i64(
            d_handle, channel, ctl.Property.POSITION) / 1000 for channel in range(4)]
        print('Current position: ', positions)
        cl_freq = [ctl.GetProperty_i32(
            d_handle, i, ctl.Property.MAX_CL_FREQUENCY) / 1000 for i in range(n_channels)]
        print('Frequency [kHz]: ', cl_freq)
        ch_type = [ctl.GetProperty_s(
            d_handle, i, ctl.Property.POSITIONER_TYPE_NAME) for i in range(n_channels)]
        print('Channel types: ', ch_type)
        velocities = [ctl.GetProperty_i64(
            d_handle, i, ctl.Property.MOVE_VELOCITY) for i in range(n_channels)]
        for i, v in zip(range(n_channels), velocities):
            if base_units[i] == ctl.BaseUnit.METER:
                print('Velocity {}: {}um/s'.format(i, v / 10**6))
            else:
                print('Velocity {}: {}deg/s'.format(i, v / 10**9))


if __name__ == "__main__":
    unittest.main()
