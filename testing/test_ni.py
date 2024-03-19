import unittest
import sys
import os

from instrumental.drivers.daq.ni import NIDAQ
sys.path.append('.')
from control.instruments.moke import Moke
from control.load_from_settings import read_settings
from control.controllers.ni_rtsi import NIcardRTSI
from control.instruments.basic.ni_instrument import NIinst
from instrumental.drivers.daq.ni import NIDAQ, Task
import numpy as np
# import matplotlib.pyplot as plt


class NItimingTest(unittest.TestCase):

    def setUp(self):
        settings_data = read_settings()
        # only keep the NI controllers
        settings_data['controllers'] = [
            cnt for cnt in settings_data['controllers'] if cnt["type"] in {"NIcardRTSI", "NIcard"}]
        # only keep the ni instruments
        settings_data['instruments'] = {
            name: inst for name, inst in settings_data["instruments"].items() if inst["type"] == "NIinst"}
        # get rid of the claibrations
        for inst in settings_data['instruments'].values():
            if 'calibration' in inst:
                inst.pop('calibration')

        # add the clock instruments
        settings_data['instruments'].update({
            "clock_in": {
                "type": "NIinst",
                "port_type": "AI",
                "controller": "NIcard",
                "ports": {
                    "Dev1/ai22": "clck",
                }
            },
            "clock_out": {
                "type": "NIinst",
                "port_type": "AO",
                "controller": "NIcard",
                "ports": {
                    "Dev2/ao11": "clckout",
                },
            }
        })
        self.settings_data = settings_data

        # self.recording_period = 1
        # self.signal = lambda t: np.logical_and(
        #     t > 0.25, t < 0.75).astype(float)
        self.recording_period = 2
        self.wait_time = 1
        self.signal = lambda t: np.sin(4 * np.pi * t)

    def test_NI_library(self):
        dev1 = NIDAQ('Dev1')
        dev2 = NIDAQ('Dev2')
        task = Task(dev1.ao2, dev2.ao2, dev1.ai23)
        task.set_timing(duration='1s', fsamp='10Hz')
        write_data = {
            'Dev1/ao2': np.linspace(0, 9, 10), 'Dev2/ao2': np.linspace(0, 9, 10)}
        result = task.run(write_data)
        print('Instrumental library result: ')
        print(result)

    def test_NI_class(self):
        ni = NIcardRTSI({"AI": ["Dev1/ai21", ], "AO": ["Dev1/ao2", ]})
        hp = NIinst(ni, "AI", ["Dev1/ai21", ])
        ni.start()
        data = hp.get_data()
        while data.empty:
            hp.wait_for_time(1)
            data = hp.get_data()
            print('Hallprobe time: ', hp.get_time())
        ni.stop()

    def test_timing(self):
        with Moke(self.settings_data) as moke:
            for inst in ['clock_in', 'clock_out']:
                moke.instruments[inst].flushing_time = self.recording_period + 3
            moke.instruments['clock_out'].wait_for_time(self.wait_time)
            t0 = moke.instruments['clock_out'].stage_data(self.signal, 1)
            data = moke.instruments['clock_in'].get_data(
                start_time=t0, end_time=t0 + self.recording_period)
            t = np.array(data.index)
            dt = t[1] - t[0]
            reading = data.to_numpy().flatten()
            # get the fourier transform and the phase of the strongest frequency
            n = len(reading)
            fft = np.fft.rfft(reading)
            freq = np.fft.rfftfreq(n, d=dt)
            idx = np.argmax(np.abs(fft))
            phase = np.angle(fft)[idx]
            time_lag = (-phase - np.pi / 2) / (2 * np.pi * freq[idx])
            assert abs(time_lag) < dt * \
                2, "Time lag needs to be smaller than one time step!"
            print('Time lag OK: {}us'.format(time_lag * 10**6))
            # data.plot()
            # plt.plot(t, self.signal(t - t[0]), label='clock output')
            # plt.legend()
            # plt.show(block=True)


if __name__ == "__main__":
    unittest.main()
