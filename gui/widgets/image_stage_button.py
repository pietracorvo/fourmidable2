from PyQt5 import QtCore
from PyQt5.QtWidgets import *
import time
import h5py
import numpy as np
import traceback

import os.path

class ImageStageButton(QPushButton):
    def __init__(self, moke, file_name=None):
        self.moke = moke
        QPushButton.__init__(self, "Save position")
        self.clicked.connect(self.button_clicked)
        if file_name is None:
            file_name = 'ImageStage_' + time.strftime("%Y%m%d-%H%M%S") + '.h5'
        self.file_name = file_name

    def button_clicked(self):
        print('Saving position and image')
        if os.path.isfile(self.file_name):
            with h5py.File(self.file_name, 'r') as file:
                pos = list(file.get('/').keys())
                nums = [int(p.split('_')[1]) for p in pos]
                n = np.max(nums) + 1

            with h5py.File(self.file_name, 'a') as file:
                grp = file.create_group('position_' + str(n))
                self.moke.instruments['Stage'].save(grp)
                self.moke.instruments['camera1'].save(grp)
        else:
            n = 1
            with h5py.File(self.file_name, 'w') as file:
                grp = file.create_group('position_' + str(n))
                self.moke.instruments['Stage'].save(grp)
                self.moke.instruments['camera1'].save(grp)
        print('Finished saving')


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    import gui.exception_handling
    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = ImageStageButton(moke)
        aw.show()
        qApp.exec_()
