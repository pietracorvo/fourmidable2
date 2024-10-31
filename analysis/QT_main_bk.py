import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QSlider
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui

# Assuming analysis.QT_functions still contains relevant functions, we keep that import.
from analysis.QT_functions import *
#from QT_functions import *

class PGCanvas(pg.PlotWidget):  # Replacing MplCanvas with pyqtgraph's PlotWidget
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('w')
        pg.setConfigOption('foreground', 'k')
        self.plotItem = self.getPlotItem()
        self.plotItem.setLabel('bottom', 'Magnetic Field', color='k',units='mT')
        self.plotItem.setLabel('left', 'MOKE Signal', color='k',units='a.u.')
        self.plotItem.addLegend()
        self.plotItem.showGrid(x=True, y=True)
        self.plotItem.getAxis('bottom').setTextPen('k')  # Bottom axis label color (black)
        self.plotItem.getAxis('left').setTextPen('k')


class QT_Analyze(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('HDF Extracter')
        self.resize(300, 150)

        # 创建一个主小部件，设置为中心窗口部件
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # 创建一个垂直布局
        layout_Main = QVBoxLayout(self.main_widget)
        layout_plot = QHBoxLayout()
        layout_canvas = QVBoxLayout()
        layout_side = QVBoxLayout()
        layout_slider = QHBoxLayout()

        # 创建一个按钮并连接到函数
        self.open_button = QPushButton('Open Files', self)
        self.open_button.clicked.connect(self.open_file)

        self.analyze_default_button = QPushButton('Start Analyzing with Default Parameters', self)
        self.analyze_default_button.clicked.connect(self.process_default_start)
        self.analyze_default_button.setEnabled(False)
        self.analyze_default_button.setVisible(False)

        self.analyze_slider_button = QPushButton('Start Analyzing with Sliders', self)
        self.analyze_slider_button.clicked.connect(self.process_slider_start)
        self.analyze_slider_button.setEnabled(False)
        self.analyze_slider_button.setVisible(False)

        # 创建一个标签显示选中文件路径
        self.filenames = QLabel('No file selected yet!', self)

        # Use PGCanvas (pyqtgraph) instead of MplCanvas (matplotlib)
        self.canvas = PGCanvas(self)
        self.canvas.setVisible(False)

        self.default_button = QPushButton('Use Default Parameters', self)
        self.default_button.clicked.connect(self.use_default_parameters)
        self.default_button.setVisible(False)

        self.slider_1 = FloatSlider(decimals=4)
        self.slider_1.setMinimum(-10)
        self.slider_1.setMaximum(10)
        self.slider_1.setValue(0)
        self.slider_2 = FloatSlider(decimals=4)
        self.slider_2.setMinimum(-20)
        self.slider_2.setMaximum(20)
        self.slider_2.setValue(0)
        self.slider_1.setVisible(False)
        self.slider_2.setVisible(False)
        self.slider_1.valueChanged.connect(self.slider_drift_changed)
        self.slider_2.valueChanged.connect(self.slider_Faraday_changed)

        self.save_button = QPushButton('Save && Next', self)
        self.save_button.setVisible(False)

        # Add widgets and layouts
        layout_Main.addWidget(self.open_button)
        layout_Main.addWidget(self.filenames)
        layout_Main.addWidget(self.analyze_default_button)
        layout_Main.addWidget(self.analyze_slider_button)
        layout_Main.addLayout(layout_plot)
        layout_plot.addLayout(layout_canvas)
        layout_canvas.addWidget(self.canvas)
        layout_plot.addLayout(layout_side)
        layout_side.addWidget(self.default_button)
        layout_side.addLayout(layout_slider)
        layout_slider.addWidget(self.slider_1)
        layout_slider.addWidget(self.slider_2)
        layout_side.addWidget(self.save_button)

    def open_file(self):
        self.analyze_default_button.setEnabled(False)
        self.analyze_default_button.setVisible(False)
        self.analyze_slider_button.setEnabled(False)
        self.analyze_slider_button.setVisible(False)
        files, _ = QFileDialog.getOpenFileNames(self, "Please select HDF files", "D:", "HDF Files (*.h5)")
        # 如果选择了文件，更新标签
        if files:
            self.resize(300, 150)
            self.file_list = list(files)
            self.filenames.setText('File selected:\n' + '\n'.join(self.file_list))
            self.analyze_default_button.setText('Start Analyzing with Default Parameters')
            self.analyze_default_button.setEnabled(True)
            self.analyze_default_button.setVisible(True)
            self.analyze_slider_button.setText('Start Analyzing with Sliders')
            self.analyze_slider_button.setEnabled(True)
            self.analyze_slider_button.setVisible(True)
            self.canvas.setVisible(False)
            self.default_button.setVisible(False)
            self.slider_1.setVisible(False)
            self.slider_2.setVisible(False)
            self.save_button.setVisible(False)
            # print(files)
        else:
            self.filenames.setText('No file selected yet!')

    def process_default_start(self):
        self.resize(300, 150)
        self.analyze_default_button.setText('Please Wait...')
        self.analyze_default_button.setEnabled(False)
        self.analyze_slider_button.setVisible(False)
        self.step = 0
        run_default_loop(self)

    def process_default_finish(self):
        print('here')
        self.close()

    def process_slider_start(self):
        self.resize(300, 500)
        self.analyze_slider_button.setText('Please Wait...')
        self.analyze_slider_button.setEnabled(False)
        self.analyze_default_button.setVisible(False)
        self.canvas.setVisible(True)
        self.slider_1.setVisible(True)
        self.slider_2.setVisible(True)
        self.default_button.setEnabled(False)
        self.default_button.setVisible(True)
        self.save_button.setVisible(True)
        # print(self.file_list)
        self.step = 0
        run_slider_loop(self)
        self.save_button.clicked.connect(lambda: run_slider_loop(self))

    def use_default_parameters(self):
        self.slider_1.setValue(self.drift_default)
        self.slider_2.setValue(self.faraday_default)

    def initialize_slider(self, x, y_raw, title, label, drift, faraday, data_out):
        self.plot_x = x
        self.plot_y = y_raw
        self.plot_title = title
        self.plot_label = label
        self.drift = drift
        self.faraday = faraday
        self.data_out = data_out
        print(drift, faraday)
        self.slider_1.setRange(drift-10 * abs(drift), drift+10 * abs(drift))
        self.slider_1.setValue(drift)
        self.slider_2.setRange(faraday-10 * abs(faraday), faraday+10 * abs(faraday))
        self.slider_2.setValue(faraday)
        self.default_button.setEnabled(True)
        self.drift_default = self.drift
        self.faraday_default = self.faraday

    def slider_drift_changed(self):
        value = self.slider_1.getFloatValue()
        self.drift = value
        plot_slider_data(self.canvas, self.plot_x, self.plot_y, self.plot_title, self.plot_label, self.drift,
                         self.faraday)
        print(f'Drift_Compensate: {value}')  # 在控制台打印滑块值

    def slider_Faraday_changed(self):
        value = self.slider_2.getFloatValue()
        self.faraday = value
        plot_slider_data(self.canvas, self.plot_x, self.plot_y, self.plot_title, self.plot_label, self.drift,
                         self.faraday)
        print(f'Faraday_Compensate: {value}')  # 在控制台打印滑块值


if __name__ == '__main__':
    DA = QApplication(sys.argv)
    DA_QT = QT_Analyze()
    DA_QT.show()
    sys.exit(DA.exec_())