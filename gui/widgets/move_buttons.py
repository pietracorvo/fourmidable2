import sys
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
import os


class MovementButtons(QWidget):
    def __init__(self, stage):
        super().__init__()
        self.stage = stage
        self.icon_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'icons')

        self.initUI()

    def initUI(self):
        self.step_label = QLabel("Step")
        self.step_label.setMaximumWidth(100)
        self.step_input = QLineEdit('50')
        self.step_input.setMaximumWidth(200)

        self.up_button = QPushButton()
        self.up_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'up-chevron.ico')))
        self.up_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.up_button.clicked.connect(self.up_button_clicked)

        self.down_button = QPushButton()
        self.down_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'down-chevron.ico')))
        self.down_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.down_button.clicked.connect(self.down_button_clicked)

        self.left_button = QPushButton()
        self.left_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'left-chevron.ico')))
        self.left_button.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.left_button.clicked.connect(self.left_button_clicked)

        self.right_button = QPushButton()
        self.right_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'right-chevron.ico')))
        self.right_button.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.right_button.clicked.connect(self.right_button_clicked)

        self.in_button = QPushButton()
        self.in_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'in_button.ico')))
        self.in_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.in_button.setMinimumHeight(70)
        self.in_button.clicked.connect(self.in_button_clicked)

        self.out_button = QPushButton()
        self.out_button.setIcon(QtGui.QIcon(
            os.path.join(self.icon_folder, 'out_button.ico')))
        self.out_button.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.out_button.setMinimumHeight(70)
        self.out_button.clicked.connect(self.out_button_clicked)

        group_layout = QVBoxLayout()
        self.step_layout = QHBoxLayout()

        self.step_layout.addWidget(self.step_label)
        self.step_layout.addWidget(self.step_input, 0, QtCore.Qt.AlignLeft)
        group_layout.addLayout(self.step_layout)

        self.button_layout = QGridLayout()
        self.button_layout.addWidget(self.up_button, 0, 1, 1, 2)
        self.button_layout.addWidget(self.left_button, 0, 0, 3, 1)
        self.button_layout.addWidget(self.in_button, 1, 1, 1, 1)
        self.button_layout.addWidget(self.out_button, 1, 2, 1, 1)
        self.button_layout.addWidget(self.right_button, 0, 3, 3, 1)
        self.button_layout.addWidget(self.down_button, 2, 1, 1, 2)

        group_layout.addLayout(self.button_layout)

        # add a group box containing controls
        group_box = QGroupBox("Smaract movement")
        group_box.setLayout(group_layout)
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        self.setLayout(main_layout)
        self.setMaximumHeight(250)

    def up_button_clicked(self):
        """Function called when up_button clicked"""
        movement_direction = '+y'
        self.move(movement_direction)

    def down_button_clicked(self):
        """Function called when down_button clicked"""
        movement_direction = '-y'
        self.move(movement_direction)

    def left_button_clicked(self):
        """Function called when left_button clicked"""
        movement_direction = '-x'
        self.move(movement_direction)

    def right_button_clicked(self):
        """Function called when right_button clicked"""
        movement_direction = '+x'
        self.move(movement_direction)

    def in_button_clicked(self):
        """Function called when in_button clicked"""
        movement_direction = '+z'
        self.move(movement_direction)

    def out_button_clicked(self):
        """Function called when out_button clicked"""
        movement_direction = '-z'
        self.move(movement_direction)

    def move(self, direction):
        """Moves the stage in one of the direction by the step in step field"""
        # check if we are already moving, pass if we are
        if self.stage.is_moving():
            return
        # get the step size
        try:
            step_size = float(self.step_input.text())
        except ValueError as err:
            print('All entries need to be numbers!')
            return
        # see if we are going negative
        if direction[0] == '-':
            step_size *= -1
        # apply the movement
        self.stage.set_position({direction[1]: step_size}, relative=True)


if __name__ == '__main__':
    import sys
    import os

    sys.path.append(os.getcwd())
    from control.instruments.moke import Moke

    # app = QApplication(sys.argv)
    # aw = MovementButtons(0)
    # aw.show()
    # qApp.exec_()

    with Moke() as moke:
        app = QApplication(sys.argv)
        stage = moke.instruments['stage']
        aw = MovementButtons(stage)
        aw.show()
        qApp.exec_()
