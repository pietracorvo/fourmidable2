import pandas as pd
import matplotlib.pyplot as plt
#
with pd.HDFStore(r'C:\Users\user\Documents\Python\MOKEpy\experiments\calibration\TimeLag_20181207-154521.h5') as store:
    # get all the relevant data
    check_out = store.get('/check_data/check_out/data')
    check_in = store.get('/check_data/check_in/data')
    # check_time = store.get('/check_data/check_time/data')
    # check_time_out = store.get('/check_data/check_time_out/data')

plt.plot(check_out.index, check_out['check_out'], label='check_out')
plt.plot(check_in.index, check_in['check_in'], label='check_in')
plt.legend()
plt.grid()

dt = check_in.index[1:]-check_in.index[:-1]
dt_out = check_out.index[1:]-check_out.index[:-1]
# check_time.plot()
# check_time_out.plot()

plt.figure()
# plt.check_in
print(dt)
print(dt_out)
plt.plot(range(len(dt)), dt)
plt.plot(range(len(dt_out)), dt_out)
plt.ylim([-1.5e-4, 1.5e-4])
plt.show()