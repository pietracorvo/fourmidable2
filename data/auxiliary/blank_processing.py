import pandas as pd
import numpy as np

with pd.HDFStore(r'C:\Users\user\Documents\Python\MOKEpy\gui/Calibration data/20181023-1623.h5') as store:
    data = store.get('hallprobe/data')
    data_mean = data.mean()[['hallprobe_A', 'hallprobe_B', 'hallprobe_C']]
    data_std = data.std()[['hallprobe_A', 'hallprobe_B', 'hallprobe_C']]
    print('mean: ', data_mean)
    print('std: ', data_std)

