import os
import sys
import data.signal_generation as signals
import numpy as np
import time
import h5py

import matplotlib.pyplot as plt

plt.ion()

if __name__ == "__main__":
    from control.instruments.moke import Moke
    freq = 19
    with Moke() as mk:
        print('Initialised moke')
        # check_out = mk.instruments['check_out']
        # check_in = mk.instruments['check_in']

        clock_in = mk.instruments['clock_in']
        clock_out = mk.instruments['clock_out']
        print('got instruments')
        # apply sin signal
        # check_out.stage_data(lambda x: np.sin(2 * np.pi * freq * x), 1 / freq, autostart=True)
        t0 = clock_out.get_time()

        period = 1 / freq
        fig = plt.figure()
        ax = fig.add_subplot(111)
        print('starting plotting')
        plt.show()

        filename = 'TimeLag_' + time.strftime("%Y%m%d-%H%M%S") + '.h5'
        print('Saving to ', filename)
        start_time = 0.000001
        i = 0
        # with h5py.File(filename, 'w') as file:
        while plt.fignum_exists(fig.number):
            print('getting data...')
            # time.sleep(1)
            start_time += 5 * period
            end_time = start_time + 5 * period
            # get the data for hallprobe and hexapole
            in_data = clock_in.get_data(
                start_time=start_time, end_time=end_time)
            out_data = clock_out.get_data(
                start_time=start_time, end_time=end_time)

            print(clock_in.get_time())
            print(clock_out.get_time())

            ax.clear()
            ax.plot(in_data.index, in_data['clock'], label='in')
            ax.plot(out_data.index, out_data['clock'], label='out')
            ax.grid()
            ax.legend()
            plt.draw()
            plt.pause(0.01)
            # save the data
            # grp = file.create_group('check_data' + str(i))
            # check_out.save(grp, start_time=start_time, end_time=end_time, wait=True)
            # check_in.save(grp, start_time=start_time, end_time=end_time, wait=True)
            i += 1

        #     # get the fft of the two signals
        #     in_fft = np.fft.rfft(in_data['check_in'])
        #     out_fft = np.fft.rfft(out_data['check_out'])
        #     freq = np.fft.rfftfreq(in_data.shape[0], in_data.index[1]-in_data.index[0])
        #
        #     # get the max of the amplitudes of the two data sets
        #     in_fft_abs = np.abs(in_fft)
        #     idx = np.argmax(in_fft_abs)
        #     print('Frequency: ', freq[idx])
        #     print('Phase difference: ', (np.angle(out_fft[idx])-np.angle(in_fft[idx]))%(2*np.pi))

        # # save 5 seconds of data
        # filename = 'TimeLag_' + time.strftime("%Y%m%d-%H%M%S") + '.h5'
        # print('Saving to ', filename)
        # with h5py.File(filename, 'w') as file:
        #     print('saving...')
        #     grp = file.create_group('check_data')
        #     check_out.save(grp, start_time=0, end_time=5, wait=True)
        #     check_in.save(grp, start_time=0, end_time=5, wait=True)
        #     # check_time.save(grp, start_time=0, end_time=5, wait=True)
        #     # check_time_out.save(grp, start_time=0, end_time=5, wait=True)
