import matplotlib

import experiments as exp
from control.instruments.moke import Moke

matplotlib.use('Qt5Agg')

import display.instrument_plotting as plotting
import matplotlib.pyplot as plt
import time

if __name__ == '__main__':
    mk = Moke()

    # ls = mk.instruments['Stage'].instruments['LinearStage']
    # ls.set_position([50,50,0])
    periods = (1.0, 1, 1)
    amplitudes = (1.0, 1, 1)
    n_loops = 3
    exp.take_loop(mk, periods=periods, amplitudes=amplitudes, n_loops=n_loops,
                  stop_event=False)
    # time.sleep(3)
    # print('starting sin')
    # exp.sin_wave(mk)
    # time.sleep(2)
    # # exp.sin_wave(mk)
    # # time.sleep(2)
    # print('Finishing test')
    del mk
