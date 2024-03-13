from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QThread, pyqtSignal
import time
from warnings import warn
import traceback
from termcolor import colored


class MovementThread(QThread):
    signal = pyqtSignal()

    def __init__(self, stages, get_values, is_relative):
        QThread.__init__(self)
        self.stages = stages
        self.direction_labels = [inst.direction_labels for inst in self.stages]
        self.get_values = get_values  # function handle
        self.is_relative = is_relative  # function handle

    # run method gets called when we start the thread
    def run(self):
        try:
            position = self.get_values()
            relative = self.is_relative()
            i = 0
            for inst in self.stages:
                n_dirs = len(inst.direction_labels)
                inst_pos = position[i:i + n_dirs]
                inst.set_position(inst_pos, wait=True, relative=relative)
                i += n_dirs
        except Exception as e:
            traceback.print_exc()
            print(colored('Wrong input!', 'red'))
        finally:
            self.signal.emit()


class MovementControl(QWidget):
    def __init__(self, stages):
        self.stages = stages
        QWidget.__init__(self)

        # add a group box containing controls
        input_box = QGroupBox("Position")

        # add move relative tick box
        self.relative_tick = QCheckBox("&Relative", self)
        self.relative_tick.setChecked(False)
        self.relative_tick.stateChanged.connect(self.relative_tick_ticked)

        # add x, y and z input fields
        position_label = dict()
        self.position_value = dict()
        for inst in self.stages:
            for key in inst.direction_labels:
                position_label[key] = QLabel(input_box)
                position_label[key].setText(key + ':')
                self.position_value[key] = QLineEdit(self)
                # add shortcut to move button
                self.position_value[key].returnPressed.connect(
                    self.move_button_clicked)
                self.position_value[key].installEventFilter(self)
        # add move button
        self.move_button = QPushButton("Move")
        self.move_button.clicked.connect(self.move_button_clicked)
        # add stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_button_clicked)
        # add back button
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.back_button_clicked)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(input_box)
        input_box.setSizePolicy(QSizePolicy.Expanding,
                                QSizePolicy.Expanding)

        input_layout = QGridLayout()

        input_layout.addWidget(self.relative_tick, 0, 1,
                               alignment=QtCore.Qt.AlignLeft)

        # write the values
        self.update_values()
        # last position values, to allow for returning after a wrong input
        self.position_history = [self.get_positions(), ]

        N = len(position_label.items())  # number of entries
        for i, label, value in zip(range(3, N + 3), position_label.values(), self.position_value.values()):
            input_layout.addWidget(label, i, 0, alignment=QtCore.Qt.AlignRight)
            input_layout.addWidget(value, i, 1, alignment=QtCore.Qt.AlignLeft)
            input_layout.addItem(QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), i, 2)

            label.setMaximumWidth(50)
            value.setMaximumWidth(200)

        input_layout.addWidget(self.move_button, i + 1,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.stop_button, i + 2,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.addWidget(self.back_button, i + 3,
                               1, alignment=QtCore.Qt.AlignCenter)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 1)
        input_layout.setColumnStretch(2, 1)

        input_box.setLayout(input_layout)
        self.setLayout(main_layout)

        # define a movement thread
        self.movement_thread = MovementThread(
            self.stages, self.get_values, self.is_relative)
        self.movement_thread.signal.connect(self.movement_finished)

        # update the position regularly
        # start the timer for updating the position
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.update_values)
        self._timer_period = 500
        self._timer.start(self._timer_period)

        # stop movement on close
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMaximumHeight(500)

    def is_relative(self):
        return self.relative_tick.isChecked()

    def move(self):
        self.move_button.setEnabled(False)
        self.relative_tick.setEnabled(False)
        self.movement_thread.start()

    def move_button_clicked(self):
        """Moves the stage to the position in input fields"""
        # # unfocus the fields
        # for value_edit in self.position_value.values():
        #     value_edit.clearFocus()
        self.position_history.append(self.get_positions())
        self.move()
        #pos=self.position_history
        #print(pos)


    def movement_finished(self):
        """Gets called when the movement is finished"""
        self.move_button.setEnabled(True)
        self.relative_tick.setEnabled(True)
        if not self._timer.isActive():
            self._timer.start(self._timer_period)

    def stop_button_clicked(self):
        """Stops the stage motion."""
        for inst in self.stages:
            inst.stop()

    def back_button_clicked(self):
        """Goes back to the last position"""
        pos = self.position_history.pop()
        self._timer.stop()
        for p, value in zip(pos, self.position_value.values()):
            value.setText(f'{p:.2f}')
        self.move()

    def get_values(self):
        try:
            result = [float(p.text()) for p in self.position_value.values()]
        except ValueError as err:
            print('All entries need to be numbers')
            raise err
        return result

    def get_positions(self):
        positions = []
        for inst in self.stages:
            positions += list(inst.get_position())
        return positions

    def get_targets(self):
        targets = []
        for inst in self.stages:
            targets += list(inst.get_target())
        return targets

    def update_values(self):
        """Gets the position and writes it in the input fields"""
        # only update the positions if none of the fields are focused
        # for value_edit in self.position_value.values():
        #     if value_edit.hasFocus():
        #         return
        if self.is_relative():
            current_position = self.get_positions()
            target_position = self.get_targets()
            position = [t - c for t,
                        c in zip(target_position, current_position)]
        else:
            position = self.get_positions()
        for p, value_edit in zip(position, self.position_value.values()):
            if not value_edit.hasFocus():
                value_edit.setText(f'{p:.2f}')

    def relative_tick_ticked(self):
        if not self._timer.isActive():
            self._timer.start(self._timer_period)

    def is_moving(self):
        for inst in self.stages:
            if inst.is_moving():
                return True
        return False

    def fileQuit(self):
        self._timer.stop()
        for inst in self.stages:
            inst.stop()
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()


if __name__ == '__main__':
    import sys
    import os
    sys.path.append(os.getcwd())
    from control.instruments.moke import Moke

    with Moke() as moke:
        app = QApplication(sys.argv)
        stage = moke.instruments['stage']
        lens1 = moke.instruments['lens1']
        lens2 = moke.instruments['lens2']
        lens3 = moke.instruments['lens3']
        instruments_to_control = [stage, lens1, lens2, lens3]
        aw = MovementControl(instruments_to_control)
        aw.show()
        qApp.exec_()
