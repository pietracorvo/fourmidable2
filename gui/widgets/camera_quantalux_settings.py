import sys
from PyQt5.QtWidgets import *
#from PyQt5.QtWidgets import QSizePolicy
from time import sleep



class CameraQuantaluxSettings(QWidget):

    def __init__(self, moke):
        super().__init__()
        self.cam = moke.instruments['quanta_camera']
        self.setWindowTitle('Camera settings for Quantalux')

        self.input_exposuretime = QDoubleSpinBox()  # in micro seconds
        self.input_exposuretime.setMinimum(self.cam.exposure_time_range_ms[0])
        self.input_exposuretime.setMaximum(self.cam.exposure_time_range_ms[1])
        self.input_exposuretime.editingFinished.connect(self.change_camera_exposure_time)

        self.input_roiorgx = QSpinBox()
        self.input_roiorgx.setMinimum(0)
        self.input_roiorgx.setMaximum(self.cam.sensor_width_pixels-2)
        self.input_roiorgy = QSpinBox()
        self.input_roiorgy.setMinimum(0)
        self.input_roiorgy.setMaximum(self.cam.sensor_height_pixels-2)
        self.input_roiwidth = QSpinBox()
        self.input_roiwidth.setMinimum(8)
        self.input_roiwidth.setMaximum(self.cam.sensor_width_pixels)
        self.input_roiheight = QSpinBox()
        self.input_roiheight.setMinimum(2)
        self.input_roiheight.setMaximum(self.cam.sensor_height_pixels)

        self.button_apply_roi = QPushButton('Apply ROI')
        self.button_apply_roi.clicked.connect(self.change_camera_roi)
        self.button_remove_roi = QPushButton('Reset ROI fo full frame')
        self.button_remove_roi.clicked.connect(self.remove_roi)

        self.input_binx = QSpinBox()
        self.input_binx.setMinimum(1)    # NOTE hard coded here for the quantalux camera
        self.input_binx.setMaximum(16)   # NOTE hard coded here for the quantalux camera
        self.input_binx.valueChanged.connect(self.change_camera_binning)
        self.input_biny = QSpinBox()
        self.input_biny.setMinimum(1)    # NOTE hard coded here for the quantalux camera
        self.input_biny.setMaximum(16)   # NOTE hard coded here for the quantalux camera
        self.input_biny.valueChanged.connect(self.change_camera_binning)

        self.input_hotpixelcorr_threshold = QDoubleSpinBox()
        self.input_hotpixelcorr_threshold.setMinimum(0.)     # NOTE hard coded here for the quantalux camera
        self.input_hotpixelcorr_threshold.setMaximum(100.)   # NOTE hard coded here for the quantalux camera
        self.input_hotpixelcorr_threshold.valueChanged.connect(self.change_hotpixelcorr_threhsold)

        # get initial values from camera
        self.update_roi_values_in_gui()
        self.update_binning_values_in_gui()
        self.input_exposuretime.setValue(self.cam.exposure_time_ms)
        self.input_hotpixelcorr_threshold.setValue((self.cam.hotpixelcorrection_threshold-65535)*100/(655-65535))

        layout_1 = QGridLayout()
        layout_1.addWidget(QLabel('Exposure time [ms]'), 1, 1)
        layout_1.addWidget(self.input_exposuretime, 1, 2)
        layout_2 = QGridLayout()
        layout_2.addWidget(QLabel('ROI Origin X'), 1, 1)
        layout_2.addWidget(self.input_roiorgx, 1, 2)
        layout_2.addWidget(QLabel('ROI Origin Y'), 2, 1)
        layout_2.addWidget(self.input_roiorgy, 2, 2)
        layout_2.addWidget(QLabel('ROI Width'), 3, 1)
        layout_2.addWidget(self.input_roiwidth, 3, 2)
        layout_2.addWidget(QLabel('ROI Height'), 4, 1)
        layout_2.addWidget(self.input_roiheight, 4, 2)
        layout_3 = QGridLayout()
        layout_3.addWidget(QLabel('Bin X'), 1, 1)
        layout_3.addWidget(self.input_binx, 1, 2)
        layout_3.addWidget(QLabel('Bin Y'), 2, 1)
        layout_3.addWidget(self.input_biny, 2, 2)
        layout_4 = QGridLayout()
        layout_4.addWidget(QLabel('Hot pixel correction'), 1, 1)
        layout_4.addWidget(self.input_hotpixelcorr_threshold, 1, 2)

        main_layout = QVBoxLayout()
        layout_0 = QGridLayout()
        info_text = QLabel('NOTE You can also use the ThorCam software to change these settings.\n(Only disconnecting the camera resets its parameters to factory defaults.)\n')
        info_text.setWordWrap(True)
        layout_0.addWidget(info_text, 1, 1)
        main_layout.addLayout(layout_0)
        main_layout.addLayout(layout_1)
        main_layout.addLayout(layout_2)
        main_layout.addWidget(self.button_apply_roi)
        main_layout.addWidget(self.button_remove_roi)
        main_layout.addLayout(layout_3)
        main_layout.addLayout(layout_4)
        self.setLayout(main_layout)

    def change_camera_exposure_time(self):
        self.cam.exposure_time_ms = self.input_exposuretime.value()

    def update_roi_values_in_gui(self):
        roi = self.cam.get_roi()
        self.input_roiorgx.setValue(roi.upper_left_x_pixels)
        self.input_roiorgy.setValue(roi.upper_left_y_pixels)
        self.input_roiwidth.setValue(roi.lower_right_x_pixels - roi.upper_left_x_pixels)
        self.input_roiheight.setValue(roi.lower_right_y_pixels - roi.upper_left_y_pixels)
        # print('\nupper_left_x_pixels', roi.upper_left_x_pixels,
        #       '\nupper_left_y_pixels', roi.upper_left_y_pixels,
        #       '\nlower_right_x_pixels', roi.lower_right_x_pixels,
        #       '\nlower_right_y_pixels', roi.lower_right_y_pixels)

    def change_camera_roi(self):
        self.cam.set_roi(
            self.input_roiorgx.value(),
            self.input_roiorgy.value(),
            self.input_roiorgx.value() + self.input_roiwidth.value(),
            self.input_roiorgy.value() + self.input_roiheight.value(),
        )
        sleep(0.1)
        self.update_roi_values_in_gui()

    def update_binning_values_in_gui(self):
        binx, biny = self.cam.binning
        self.input_binx.setValue(binx)
        self.input_biny.setValue(biny)

    def change_camera_binning(self):
        self.cam.set_binning((self.input_binx.value(), self.input_biny.value()))
        sleep(0.1)
        self.update_binning_values_in_gui()

    def change_hotpixelcorr_threhsold(self):
        val_cam = int((655-65535)/100 * self.input_hotpixelcorr_threshold.value() + 65535)   # here map from 0-100 in gui to 65535-655 in camera
        self.cam.set_hotpixelcorrection(val_cam)
        sleep(0.1)
        val_gui = (self.cam.hotpixelcorrection_threshold - 65535)*100/(655-65535)
        self.input_hotpixelcorr_threshold.setValue(val_gui)

    def remove_roi(self):
        self.cam.reset_roi_if_roi_selected()
        sleep(0.1)
        self.update_roi_values_in_gui()



if __name__ == '__main__':
    from control.instruments.moke import Moke

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = CameraQuantaluxSettings(moke)
        aw.show()
        qApp.exec_()
