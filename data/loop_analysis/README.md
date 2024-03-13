# Loop analysis

Basic library for analysing MOKE loops data created by the 3D MOKE software.

Usage:
```python
from loop_analysis import *

file_path = "./loop_file.h5"
# get the raw data
raw_data = get_file_data(file_path, group='Loop Map/{}/loops'.format(pt))
# average over the loops
averaged_data = get_averaged_loop(raw_data)
# get the kerr signal
data_kerr = get_kerr_signal(averaged_data, 
                            plot=True, 
                            stage_angle=15)
# plot the kerr signal
plot_moke(data_kerr)
```