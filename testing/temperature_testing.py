import threading
import time

import h5py
import pandas as pd

import data.signal_generation as signals
from control.instruments.moke import Moke
from data.auxiliary.saving import save_calibration
from experiments.basic import set_baseline

from gui.widgets.canvas import DynamicMokePlot
import sys
from PyQt5.QtWidgets import *
import traceback
from termcolor import colored

import copy


def saving_worker(store, saving_interval, hp, temp, stop_event, magnet):
    try:
        t0 = magnet.get_time()
        magnets_stopped = False
        while not stop_event.is_set():
            # get the data
            print('starting acquisition')
            hp_data = hp.get_data(start_time=t0, end_time=t0 + saving_interval, wait=True)
            temp_data = temp.get_data(start_time=t0, end_time=t0 + saving_interval, wait=True)
            magnet_data = magnet.get_data(start_time=t0, end_time=t0 + saving_interval, wait=True)
            t0 += saving_interval
            # average over the data
            temp_mean = temp_data.mean()
            hp_mean = hp_data.mean()
            magnet_mean = magnet_data.mean()
            # print the current temperature
            print('Current temperature: \n', copy.deepcopy(temp_mean))
            if (temp_mean > 55).any() and not magnets_stopped:
                print('Coils too hot!')
                print('Stopping magnets')
                magnet.stage_data(signals.get_const_signal([0] * 3), 1, autostart=True)
                magnets_stopped = True
            if magnets_stopped and (temp_mean<30).all():
                break
            # construct a pandas dataframe from this
            df = pd.concat((temp_mean.to_frame().T, hp_mean.to_frame().T, magnet_mean.to_frame().T), axis=1)
            df.index = [t0]
            df.index.name = 't'
            # save that data
            store.append('data', df, data_columns=True)
            print('data saved')
        store.close()
        print('Experiment finished')
    except:
        traceback.print_exc()


if __name__ == "__main__":
    print(colored("Make sure that the safety notices from temperature calibration are lifted!", "red"))
    # initialise moke
    with Moke() as mk:
        # set the baseline
        set_baseline(mk)

        # define the field magnitude in V
        field_mag = 5
        # define saving interval
        saving_interval = 5

        # get the instruments
        magnet = mk.instruments['hexapole']
        hp = mk.instruments['hallprobe']
        temp = mk.instruments['temperature']

        # apply the field
        magnet.stage_data(signals.get_const_signal([field_mag] * 3), 1, autostart=True)
        # create a file to track the field and temperature
        filename = "temperature_testing_" + time.strftime("%Y%m%d-%H%M") + '.h5'
        with h5py.File(filename, 'w') as file:
            # save the calibration
            calib_grp = file.create_group('calibration')
            save_calibration([hp, temp], calib_grp)
        # create pandas store for the data
        store = pd.HDFStore(filename)

        stop_event = threading.Event()
        saving_thread = threading.Thread(target=saving_worker, args=(store, saving_interval, hp, temp, stop_event, magnet))
        saving_thread.daemon = True
        saving_thread.start()


        app = QApplication(sys.argv)
        plotting = DynamicMokePlot(mk)
        print('starting to plot')
        plotting.show()
        qApp.exec_()

        stop_event.set()
        saving_thread.join()
