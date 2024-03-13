import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

with pd.HDFStore(r'C:\Users\user\Documents\Python\MOKEpy\gui\Calibration data\field_magnitude_testing20181025-1336.h5') as store:
    hp_data = store.get('hallprobe/data')
    mag_data = store.get('hexapole/data')

x = mag_data['magnet_A'][:]
for key in ['hallprobe_A', 'hallprobe_B', 'hallprobe_C']:
    plt.plot(x, hp_data[key][:-1], label=key.split('_')[1])
plt.legend()
plt.xlabel('I [A]')
plt.ylabel('B [mT]')
plt.grid()
plt.title('Field magnitude experiment')
# f = plt.figure()
# # get the data where mag is 0
# indx = np.array(x)==0
# for key in ['hallprobe_A', 'hallprobe_B', 'hallprobe_C']:
#     h = hp_data[key][:-1][indx]
#     t = hp_data["t"][:-1][indx]
#     print(h.shape)
#     plt.scatter(t, h, label=key.split('_')[1])

plt.show()


