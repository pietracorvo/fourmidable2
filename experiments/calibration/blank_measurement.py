import os
import sys
sys.path.append(os.getcwd())
import time
import h5py


def blank_measurement(moke, saving_interval=5):
    magnet = moke.instruments['hexapole']
    t0 = magnet.get_time()
    print('Waiting for ', saving_interval, 's')
    magnet.wait_for_time(t0 + saving_interval)
    filename = time.strftime("moke%Y%m%d-%H%M") + '.h5'
    print('Saving...')
    with h5py.File(filename, 'w') as file:
        moke.save(file)
    print('Finished saving')


if __name__ == "__main__":
    from control.instruments.moke import Moke
    with Moke() as moke:
        blank_measurement(moke)
