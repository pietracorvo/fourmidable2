import numpy as np
from experiments.basic import deGauss
import time
import h5py
import data.signal_generation as signals
from data.auxiliary.sphere_points import fibonacci_sphere


def sphere_loop_map(moke, sphere_points=100, amplitude=4, period=0.5, n_loops=5, skip_loops=0):
    """Does a 3d map of the moke switching fields

    Args:
        moke: handle to moke object
        period: period of sin wave signal
        amplitude: amplitude of the signal
        n_loops: the number of loops required
    """
    # get instruments which we are going to use for convenience
    magnet = moke.instruments['hexapole']
    hp = moke.instruments['hallprobe']
    woll = moke.instruments['wollaston']
    # create a file to save the experiment in
    filename = '3dmap_' + time.strftime("%Y%m%d-%H%M%S") + '.h5'

    # get the points of the sphere
    points = fibonacci_sphere(sphere_points)
    point_amplitudes = list(amplitude * np.array(points))

    # set the flushing time to be appropriate
    magnet.flushing_time = np.max([period + 1, 5])
    hp.flushing_time = np.max([period + 1, 5])
    woll.flushing_time = np.max([period + 1, 5])

    print('Saving to ', filename)
    with h5py.File(filename, 'w') as f:
        # loop over the points and store the results
        for i, amp in enumerate(point_amplitudes):
            print('Point ', i, '/', sphere_points)
            deGauss(moke)
            # when degaussing done, start the sin-wave
            magnet.stage_data(signals.sin_signal(amp, [period] * 3), period, autostart=True)
            # start when the magnet starts outputting the data
            start_time = magnet.get_next_refresh_time() + period * skip_loops
            end_time = start_time + period * n_loops

            # create the saving group and add the point of the sphere to it
            grp = f.create_group('point_' + str(i))
            grp.create_dataset("point", data=amp / amplitude)
            grp.attrs['amplitudes'] = np.array(amp)
            grp.attrs['period'] = np.array(period)

            # save the instruments
            hp.save(grp, start_time=start_time, end_time=end_time, wait=True)
            woll.save(grp, start_time=start_time, end_time=end_time, wait=True)
            magnet.save(grp, start_time=start_time, end_time=end_time, wait=True)

    magnet.stage_data(signals.zeros_signal(), 1, autostart=True)
    print('Experiment finished')


if __name__ == "__main__":
    from control.instruments.moke import Moke

    with Moke() as moke:
        pass
        # sphere_loop_map(moke)
