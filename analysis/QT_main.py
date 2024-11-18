import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGraphicsTextItem, QFileDialog, QLabel, QSlider,QCheckBox
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
        #self.plotItem.setDefaultPadding(padding=5)
        self.plotItem.setLabel('bottom', 'Magnetic Field', color='k',units='mT')
        self.plotItem.setLabel('left', 'MOKE Signal', color='k',units='a.u.')
        self.plotItem.addLegend()
        self.plotItem.setTitle('Please wait while loading images...')
        self.plotItem.showGrid(x=True, y=True)
        #self.setStyleSheet("border: 2px solid black;")
        self.plotItem.getAxis('bottom').setTextPen('k')  # Bottom axis label color (black)
        self.plotItem.getAxis('left').setTextPen('k')
        self.viewbox = self.getViewBox()
        self.viewbox.setBorder(color='k',width=0)


class QT_Analyze(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('HDF Extracter')

        # 创建一个主小部件，设置为中心窗口部件
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # 创建一个垂直布局
        self.layout_Main = QVBoxLayout(self.main_widget)
        self.layout_plot = QHBoxLayout()
        self.layout_canvas = QVBoxLayout()
        self.layout_side = QVBoxLayout()
        self.layout_slider = QHBoxLayout()
        self.slider_buttons = QHBoxLayout()

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

        self.checkbox_drift = QCheckBox("x10")
        self.checkbox_drift.stateChanged.connect(self.drift_x10)
        self.checkbox_drift.setLayoutDirection(Qt.RightToLeft)

        self.checkbox_faraday = QCheckBox("x10")
        self.checkbox_faraday.stateChanged.connect(self.faraday_x10)
        self.checkbox_faraday.setLayoutDirection(Qt.RightToLeft)

        # 创建一个标签显示选中文件路径
        self.filenames = QLabel('No file selected yet!', self)

        #image_stack = np.random.randint(0, 256, (10, 512, 512)).astype(np.uint16)
        #self.tiffcanvas = TiffImageViewer(image_stack)

        self.tiffcanvas = TiffImageViewer()

        # Use PGCanvas (pyqtgraph) instead of MplCanvas (matplotlib)
        self.canvas = PGCanvas(self)
        self.canvas.setMinimumWidth(400)
        self.canvas.setVisible(False)

        self.default_button = QPushButton('Use Default', self)
        self.default_button.clicked.connect(self.use_default_parameters)
        self.default_button.setVisible(False)
        self.default_button.setEnabled(False)

        self.slider_1_label = create_rotated_label('Drift Compensation',90)
        self.slider_1 = FloatSlider(decimals=4,direction = Qt.Vertical)
        self.slider_1.setMinimum(-10)
        self.slider_1.setMaximum(10)
        self.slider_1.setValue(0)
        self.slider_2_label = create_rotated_label('Faraday Compensation',90)
        self.slider_2 = FloatSlider(decimals=4,direction = Qt.Vertical)
        self.slider_2.setMinimum(-20)
        self.slider_2.setMaximum(20)
        self.slider_2.setValue(0)
        self.slider_1.setVisible(False)
        self.slider_2.setVisible(False)
        self.slider_1.valueChanged.connect(self.slider_drift_changed)
        self.slider_2.valueChanged.connect(self.slider_Faraday_changed)
        self.drift_10 = 1
        self.faraday_10 = 1

        self.save_button = QPushButton('Save && Next', self)
        self.save_button.setVisible(False)
        self.save_button.setEnabled(False)

        # Add widgets and layouts
        self.layout_Main.addWidget(self.open_button)
        self.layout_Main.addWidget(self.filenames)
        self.layout_Main.addWidget(self.analyze_default_button)
        self.layout_Main.addWidget(self.analyze_slider_button)
        self.layout_Main.addLayout(self.layout_plot)
        
        self.layout_plot.addWidget(self.tiffcanvas)
        self.layout_plot.addLayout(self.layout_canvas)
        self.layout_canvas.addWidget(self.canvas)
        self.layout_plot.addLayout(self.layout_side)
        self.layout_side.addWidget(self.default_button)
        self.layout_side.addLayout(self.layout_slider)
        self.layout_slider.addWidget(self.slider_1)
        self.layout_slider.addWidget(self.slider_1_label)
        self.layout_slider.addWidget(self.slider_2)
        self.layout_slider.addWidget(self.slider_2_label)
        self.layout_side.addLayout(self.slider_buttons)
        self.slider_buttons.addWidget(self.checkbox_drift)
        self.slider_buttons.addWidget(self.checkbox_faraday)
        self.layout_side.addWidget(self.save_button)


        self.toggle_layout_visibility(self.layout_plot,'off')
        self.resize(300, 150)

    def toggle_layout_visibility(self,layout,condition):
        # 切换所有布局及其子布局中的控件的可见性
        self.toggle_visibility(layout,condition)

    def toggle_visibility(self,layout,condition):
        for i in range(layout.count()):
            item = layout.itemAt(i)  # 获取布局中的项
            if item is None:
                continue
            widget = item.widget()  # 尝试获取控件
            if widget:  # 如果是 QWidget，则切换可见性
                if condition == 'on':
                    widget.show()
                else:
                    widget.hide()
            else:  # 如果是 QLayout，则递归处理
                nested_layout = item.layout()
                if nested_layout:
                    self.toggle_visibility(nested_layout,condition)

    def drift_x10(self,state):
        if state == 0:
            self.drift_10 = 1
        else:
            self.drift_10 = 10
        self.update_slider(self.drift_10, self.faraday_10)

    def faraday_x10(self,state):
        if state == 0:
            self.faraday_10 = 1
        else:
            self.faraday_10 = 10
        self.update_slider(self.drift_10, self.faraday_10)

    def open_file(self):
        #self.analyze_default_button.setEnabled(False)
        #self.analyze_default_button.setVisible(False)
        #self.analyze_slider_button.setEnabled(False)
        #self.analyze_slider_button.setVisible(False)
        files, _ = QFileDialog.getOpenFileNames(self, "Please select HDF files", "D:", "HDF Files (*.h5)")
        # 如果选择了文件，更新标签
        if files:
            self.file_list = list(files)
            self.filenames.setText('File selected:\n' + '\n'.join(self.file_list))
            self.analyze_default_button.setText('Start Analyzing with Default Parameters')
            self.analyze_default_button.setEnabled(True)
            self.analyze_default_button.setVisible(True)
            self.analyze_slider_button.setText('Start Analyzing with Sliders')
            self.analyze_slider_button.setEnabled(True)
            self.analyze_slider_button.setVisible(True)
            #self.canvas.setVisible(False)
            #self.default_button.setVisible(False)
            #self.slider_1.setVisible(False)
            #self.slider_2.setVisible(False)
            #self.save_button.setVisible(False)
            self.toggle_layout_visibility(self.layout_plot,'off')
            # print(files)
        else:
            self.filenames.setText('No file selected yet!')
        self.toggle_layout_visibility(self.layout_plot,'off')
        self.resize(300, 150)

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
        self.analyze_slider_button.setText('Please Wait...')
        self.analyze_slider_button.setEnabled(False)
        self.analyze_default_button.setVisible(False)
        #self.toggle_layout_visibility(self.layout_plot,'on')
        self.canvas.clear()
        self.canvas.getPlotItem().setTitle('Please wait while loading images...')
        #self.canvas.setVisible(True)
        #self.slider_1.setVisible(True)
        #self.slider_2.setVisible(True)
        #self.default_button.setEnabled(False)
        #self.default_button.setVisible(True)
        #self.save_button.setVisible(True)
        # print(self.file_list)
        self.step = 0
        run_slider_loop(self)
        self.save_button.clicked.connect(lambda: run_slider_loop(self))

    def use_default_parameters(self):
        self.slider_1.setRange(self.drift_default-10 * abs(self.drift_default), self.drift_default+10 * abs(self.drift_default))
        self.slider_2.setRange(self.faraday_default-10 * abs(self.faraday_default), self.faraday_default+10 * abs(self.faraday_default))
        self.slider_1.setValue(self.drift_default)
        self.slider_2.setValue(self.faraday_default)
        self.checkbox_drift.setChecked(False)
        self.checkbox_faraday.setChecked(False)

    def initialize_slider(self, x, y_raw, title, label, drift, faraday, data_out,image_stack_ave,roi_mask,image_stack_masked):
        self.resize(1100, 660)
        self.plot_x = x
        self.plot_y = y_raw
        self.plot_title = title
        self.plot_label = label
        self.drift = drift
        self.faraday = faraday
        self.data_out = data_out
        self.image_stack_ave = image_stack_ave#.astype(np.uint16)
        #print(self.image_stack_ave[0])
        self.roi_mask = roi_mask
        #print(self.roi_mask)
        #print(np.min(image_stack_masked[0]))
        #self.clear_layout_plot()
        self.tiffcanvas.image_show(self.image_stack_ave,self.roi_mask)
        #self.tiffcanvas = ImageAdjustWidget(self.image_stack_ave)
        self.toggle_layout_visibility(self.layout_plot,'on')
        print(drift, faraday)
        self.slider_1.setRange(drift-10 * abs(drift), drift+10 * abs(drift))
        self.slider_1.setValue(drift)
        self.slider_2.setRange(faraday-10 * abs(faraday), faraday+10 * abs(faraday))
        self.slider_2.setValue(faraday)
        self.default_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.drift_default = self.drift
        self.faraday_default = self.faraday

    def update_slider(self, drift_10, faraday_10):
        self.slider_1.setRange(self.drift-drift_10*10 * abs(self.drift_default), self.drift+drift_10*10 * abs(self.drift_default))
        self.slider_1.setValue(self.drift)
        self.slider_2.setRange(self.faraday-faraday_10*10 * abs(self.faraday_default), self.faraday+faraday_10*10 * abs(self.faraday_default))
        self.slider_2.setValue(self.faraday)

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