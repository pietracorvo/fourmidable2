import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

with pd.HDFStore(r'D:\OneDrive - University Of Cambridge\PhD\3DMOKE\Calibration data\Temperatue_testing\temperature_testing_20181025-1511_250mA.h5') as store:
    data = store.get('data')

data.reset_index(inplace=True, drop=True)
data.index = data.index - data.index[0]
fields_off_index = data['magnet_A'].idxmin()
plt.plot(data.index, data['temperature_A'], label='A')
plt.plot(data.index, data['temperature_B'], label='B')
plt.plot(data.index, data['temperature_C'], label='C')

# add the fields off line
plt.axvline(x=data.index[fields_off_index], label='fields off', color='k')

plt.legend()
plt.xlabel('t [s]')
plt.ylabel(r'T [°C]')
plt.grid()
plt.title('Heating experiment, 2.5A')

plt.show()

