import numpy as np
import sys
import os
sys.path.append(os.getcwd())
from control.instruments.moke import Moke
from data.signal_generation import get_const_signal
import time

if __name__ == "__main__":

    with Moke() as moke:
        laser = moke.instruments['laser']
        print('Applying signal')
        laser.stage_data(get_const_signal([3]), 1)
        time.sleep(5)
