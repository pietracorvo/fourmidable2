import time

import h5py

import display.instrument_plotting as inst_plt
import threading
import copy
from gui.widgets.camera_window import CameraWindow
from PyQt5.QtWidgets import *
import sys

import traceback


def take_images(moke, stop_event=None, time_step=10):
    """Takes an image every time_step seconds"""
    camera = moke.instruments['camera1']
    temp_sensor = moke.instruments['bighall_temp']
    temp_sensor.flushing_time = time_step + 5
    start_time = temp_sensor.get_time()
    # create the file for saving
    filename = "image_taking_" + time.strftime("%Y%m%d-%H%M") + '.h5'
    indx = 0
    try:
        with h5py.File(filename, 'w') as file:
            while stop_event is None or not stop_event.is_set():
                indx += 1
                print('Taking image ', indx)
                img_grp = file.create_group('img_' + str(indx))
                camera.save(img_grp)
                temp_sensor.save(img_grp, start_time=start_time)
                start_time = temp_sensor.get_time()
                time.sleep(time_step)
    except:
        traceback.print_exc()


if __name__ == "__main__":
    from control.instruments.moke import Moke
    # initialise moke
    with Moke() as moke:
        stop_event = threading.Event()
        position_thread = threading.Thread(
            target=take_images, args=(moke, stop_event))
        position_thread.daemon = True
        position_thread.start()

        # start showing the camera

        app = QApplication(sys.argv)
        aw = CameraWindow(moke.instruments['camera1'])
        aw.show()
        qApp.exec_()
        stop_event.set()
        position_thread.join()
