from PyQt5 import QtCore
from PyQt5.QtWidgets import *


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())



class BackgroundSubstractionLive(QWidget):
    def __init__(self, moke):
        self.hexapole = moke.instruments['hexapole']
        self.moke = moke
        QWidget.__init__(self)


        # add apply fields button
        self.apply_button = QPushButton("Apply fields")

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.apply_button)
        self.setLayout(main_layout)