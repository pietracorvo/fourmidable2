import sys
import os
sys.path.append('.')
from control.controllers.ni import NIcard
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
    # ni = NIcard({"AI": ["Dev1/ai21", ], "AO": ["Dev1/ao2", ]})
    # hp = NIinst(ni, "AI", ["Dev1/ai21", ])
    # inst = NIinst(ni, "AO", ["Dev1/ao2", ])
    # ni.start()
    # data = hp.get_data()
    # while data.empty:
    #     time.sleep(1)
    #     data = hp.get_data()
    #     # print(data)
    #     print(hp.get_time())
    # data = hp.get_data(start_time=1, end_time=2, wait=True)
    # print(data)
    # print(hp.get_last_data_point())
    # # check change of flushing
    # print('checking flushing...')
    # hp.flushing_time = 3
    # t = hp.get_time()
    # print(t)
    # data = hp.get_data(start_time=t, end_time=t + hp.flushing_time + 1)
    # print(data)
    # ni.stop()

    # # Checking monotonicity
    # # ====================
    # ni = NIcard({"AI": ["Dev1/ai21", ]})
    # hp = NIinst(ni, "AI", ["Dev1/ai21", ])
    # ni.start()
    # data = hp.get_data()
    # while data.empty:
    #     time.sleep(1)
    #     data = hp.get_data()
    # while True:
    #     print('got data')
    #     data = hp.get_data(end_time=-0.5, wait=True)
    #     t = np.array(data.index)
    #     is_monotonous = np.all(t[1:] - t[:-1] > 0)
    #     if not is_monotonous:
    #         print('error!')
    #         print(data)
    #         break
    #     time.sleep(0.1)
    # ni.stop()

    # # Checking the outputs
    # # ====================
    # ni = NIcard({"AO": ["Dev2/ao11", ], 'clock': "Dev2/ao6"})
    # inst = NIinst(ni, "AO", ["Dev2/ao11", ])
    # ni.start()
    # data = inst.get_data()
    # while data.empty:
    #     time.sleep(1)
    #     data = inst.get_data()
    #     print(data)
    #     print(inst.get_time())
    # data = inst.get_data(start_time=1, end_time=2, wait=True)
    # t = np.linspace(0, 1, 100)
    # inst.stage_interp(t, np.sin(t)[:, np.newaxis])
    # start_time = inst.get_time()
    # data = inst.get_data(start_time=start_time,
    #                      end_time=start_time + 1, wait=True)
    # print(data)
    # print(start_time)
    # ni.stop()

    # # Checking subsampling
    # # ====================
    # ni = NIcard({"AI": ["Dev1/ai21", ]})
    # hp = NIinst(ni, "AI", ["Dev1/ai21", ], subsample=100)
    # ni.start()
    # data = hp.get_data(start_time=1, end_time=2, wait=True)
    # print(data)
    # print(hp.get_last_data_point())
    # ni.stop()

    # # Checking plotting
    # # ====================
    # ni = NIcard({"AI": ["Dev1/ai21", ]})
    # hp = NIinst(ni, "AI", ["Dev1/ai21", ], subsample=100, name='temperature')
    # ni.start()
    # # start plotting
    # app = QApplication(sys.argv)
    # aw = NIPlotting(hp, self_run=True, data_per_second=1)
    # aw.plt.show()d
    # app.exec_()
    # ni.stop()

    # Checking MOKE
    with Moke() as moke:
        print(moke.instruments['hallprobe'].get_data(start_time=1, end_time=2))
