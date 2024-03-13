import time
import h5py
import numpy as np
from experiments.basic import deGauss
import display.instrument_plotting as inst_plt
from data.signal_generation import stack_funs, get_const_fun


if __name__ == "__main__":
    from control.instruments.moke import Moke
    # define the time frame to be used
    rampup_time = 10

    # initialise moke
    with Moke() as mk:
        # get the instruments
        NI = mk.controller["NIcard1"]
        NI2 = mk.controller["NIcard2"]
        magnet = mk.instruments['hexapole']
        hp = mk.instruments['hallprobe']
        NI.flushing_time = 20
        NI2.flushing_time = 20
        # set the baseline
        deGauss(mk)
        time.sleep(0.1)

        # apply the field
        def fun(t):
            t_max = np.max(t)
            output = t * 10 / t_max
            return output
        outputfun, outputtime = stack_funs(
            [fun, get_const_fun(0)], [rampup_time, 5])
        t0 = magnet.get_time()
        print('Time now: ', time.time())
        print(NI.get_time())
        print(NI.get_time("t_out"))
        print(NI2.get_time())
        print(NI2.get_time('t_out'))
        magnet.stage_data([outputfun] * 3, outputtime, autostart=True)
        # create a file to track the field and temperature
        filename = "field_magnitude_testing" + \
            time.strftime("%Y%m%d-%H%M") + '.h5'
        with h5py.File(filename, 'w') as file:
            # save the instruments
            print('Waiting for the save')
            hp.save(file, start_time=t0, end_time=t0 +
                    rampup_time + 1, wait=True)
            print('waiting for magnet')
            magnet.save(file, start_time=t0, end_time=t0 +
                        rampup_time + 1, wait=True)
        print('Testing finished')
