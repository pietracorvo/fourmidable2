from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt5.QtWidgets import QSizePolicy
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from experiments.basic import switch_laser


class LaserButton(QWidget):
    def __init__(self, moke):
        QWidget.__init__(self)
        self.moke = moke
        self.laser = moke.instruments['laser']
        self.high_voltage = 3
        self.low_voltage = 0

        # set the current laser state
        self.laser_state = self.laser_on()
        # define the button and text
        self.toggle_button = QPushButton()
        button_text = self.get_button_text(self.laser_state)
        self.toggle_button.setText(button_text)
        self.toggle_button.clicked.connect(self.toggle_button_clicked)

        # set layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.toggle_button)
        self.setLayout(main_layout)

        # timer for updating the state of the button
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_button_text)
        self.update_timer.start(300)

    def laser_on(self):
        value = self.laser.get_last_data_point().values[0]
        if value > (self.high_voltage + self.low_voltage) / 2:
            return True
        else:
            return False

    def set_laser_state(self, state):
        """Sets the state of the laser to either 'high' or 'low'"""
        switch_laser(self.moke, state)

    def get_button_text(self, state):
        return 'Laser off' if state else 'Laser on'

    def update_button_text(self):
        current_state = self.laser_on()
        if current_state != self.laser_state:
            text = self.get_button_text(current_state)
            self.toggle_button.setText(text)
            self.laser_state = current_state

    def toggle_button_clicked(self):
        # toggle laser
        self.set_laser_state(not self.laser_on())


if __name__ == '__main__':
    # from unittest.mock import Mock
    # moke = Mock()
    # moke.instruments = {'laser': Mock()}
    # laser = moke.instruments['laser']
    # mock_laser_data = pd.DataFrame([3], columns=['laser'])
    # laser.get_last_data_point = Mock(return_value=mock_laser_data)
    # app = QApplication(sys.argv)
    # aw = LaserButton(moke)
    # aw.show()
    # qApp.exec_()
    from control.instruments.moke import Moke

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = LaserButton(moke)
        aw.show()
        qApp.exec_()
