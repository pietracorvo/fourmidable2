from control.instruments.moke import Moke
from display.instrument_plotting import MokePlotting
from experiments.basic import take_loop
import data.signal_generation as signals
import numpy as np
import time

# import traceback
# import warnings
# import sys
#
# def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
#
#     log = file if hasattr(file,'write') else sys.stderr
#     traceback.print_stack(file=log)
#     log.write(warnings.formatwarning(message, category, filename, lineno, line))
#
# warnings.showwarning = warn_with_traceback

import matplotlib.pyplot as plt

if __name__=="__main__":
    mk = Moke()
    time.sleep(2)
    data = mk.instruments["hallprobe"].get_data()
    print(data)
    mk.__exit__()
    # t = np.linspace(0, 4, 40000)
    # degauss_time = 3
    # zeros_time = 1
    # degauss_fun, dz_time = signals.stack_funs([signals.get_deGaussing_fun(), lambda x: np.zeros(len(x))],
    #                                           [degauss_time, zeros_time])
    # degauss_fun(t)
    #
    # with Moke() as mk:
    #     take_loop(mk)
