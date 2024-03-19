import sys
import os
sys.path.append('.')
from control.controllers.ni_rtsi import NIcardRTSI
from control.instruments.basic.ni_instrument import NIinst
import numpy as np
from display.instrument_plotting import NIPlotting
from PyQt5.QtGui import QApplication
from instrumental.drivers.daq.ni import NIDAQ
from control.instruments.moke import Moke

import time


if __name__ == "__main__":
    # # Checking the inputs
    # # == == == == == == == == == ==
    # ni = NIcardRTSI({"AI": ["Dev1/ai22", "Dev1/ai23"],
    #                  "AO": ["Dev1/ao2", "Dev2/ao11"]})
    # clockin = NIinst(ni, "AI", ["Dev1/ai23", ])
    # clockout = NIinst(ni, "AO", ["Dev2/ao11", ])
    # inst = NIinst(ni, "AO", ["Dev1/ao2", ])
    # ni.start()
    # data = clockin.get_data()
    # while data.empty:
    #     time.sleep(1)
    #     data = clockin.get_data()
    #     # print(data)
    #     print(clockin.get_time())
    # data = clockin.get_data(start_time=1, end_time=2, wait=True)
    # print(data)
    # print(clockin.get_last_data_point())
    # # check change of flushing
    # print('checking flushing...')
    # clockin.flushing_time = 3
    # t = clockin.get_time()
    # print(t)
    # data = clockin.get_data(start_time=t, end_time=t +
    #                         clockin.flushing_time + 1)
    # print(data)
    # ni.stop()

    # Checking MOKE
    # ====================
    with Moke() as moke:
        hp = moke.instruments['hallprobe']
        hx = moke.instruments['hexapole']
        time.sleep(1)
        t0 = hp.get_time()
        t1 = hx.get_time()
        print('hp: ', t0)
        print('hx: ', t1)
        print(moke.instruments['hallprobe'].get_data(start_time=1, end_time=2))
