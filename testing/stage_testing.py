import time

import h5py

import display.instrument_plotting as inst_plt
from control.instruments.moke import Moke
import threading
import copy
from gui.widgets.camera_window import CameraWindow
from PyQt5.QtWidgets import *
import sys

import traceback


def position_worker(stage, camera, positions, stop_event):
    # create the file for saving
    filename = "stage_testing_" + time.strftime("%Y%m%d-%H%M") + '.h5'
    move_step = 0
    pos_indx = 0
    try:
        with h5py.File(filename, 'w') as file:
            while not stop_event.is_set():
                move_step += 1
                pos = positions[pos_indx % len(positions)]
                print('Move ' + str(copy.deepcopy(move_step)))
                print('Moving to position ', copy.deepcopy(pos))
                pos_grp = file.create_group('move_' + str(move_step))
                stage.set_position(pos, wait=True)
                pos_indx += 1
                camera.save(pos_grp)
                stage.save(pos_grp)
    except:
        traceback.print_exc()


if __name__ == "__main__":
    positions = [
        [2693.88159792773, -787.2860299999991, -70.1119952102431, 45.002, -50.0, 0.0],
        [-296.25804451176896, -770.868859999999, -69.67347059909609, 45.00209, -50.0, 0.0],
        [-289.86252720793254, 2230.935330000005, -69.3952294280972, 45.00217, -50.0, 0.0]
    ]

    # initialise moke
    with Moke() as mk:
        # get the required instruments
        camera = mk.instruments['camera1']
        stage = mk.instruments['Stage']

        stop_event = threading.Event()
        position_thread = threading.Thread(target=position_worker, args=(stage, camera, positions, stop_event))
        position_thread.daemon = True
        position_thread.start()

        # start showing the camera

        app = QApplication(sys.argv)
        aw = CameraWindow(camera)
        aw.show()
        qApp.exec_()
        stop_event.set()
        position_thread.join()
