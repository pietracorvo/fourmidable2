import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QRect, QPoint, QTimer,QRectF
from PyQt5.QtWidgets import QApplication, QSlider, QWidget, QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene,QGraphicsTextItem, QPushButton, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
import h5py
import math as m
import numpy as np
import pyqtgraph as pg
from tifffile import imwrite
import matplotlib.pyplot as plt

class ImageAdjustWidget(QWidget):
    def __init__(self,image_stack,roi_mask):
        super().__init__()
        pg.setConfigOption('background', 'w')
        self.image_stack = image_stack
        self.roi_mask_auto = roi_mask
        print(self.roi_mask_auto)
        self.calculate_BC(self.image_stack[0])
        #print(self.image_B,self.image_C)
        self.width = self.image_stack[0].shape[0]
        self.height = self.image_stack[0].shape[1]
        self.layout = QVBoxLayout()
        # Image display widget (with pan/zoom and color bar disabled)
        self.image_view = pg.ImageView(view=pg.PlotItem())  # Remove the default UI
        self.image_view.ui.histogram.hide()  # Remove the color bar
        self.image_view.ui.roiBtn.hide()  # Remove the ROI button
        self.image_view.ui.menuBtn.hide()  # Remove the menu button
        self.image_view.view.setMouseEnabled(x=False, y=False)  # Disable image movement
        self.image_view.getView().hideAxis('left')
        self.image_view.getView().hideAxis('bottom')
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.current_index = 0

        # Auto-adjust button for automatic brightness/contrast calculation
        self.auto_button = QPushButton('Auto Adjust BC', self)
        self.auto_button.clicked.connect(self.auto_adjust)
        self.layout.addWidget(self.auto_button)

        self.slider_panel = QHBoxLayout()
        self.layout.addLayout(self.slider_panel)

        # Brightness slider
        self.brigheness_panel = QVBoxLayout()
        self.slider_panel.addLayout(self.brigheness_panel)
        self.brightness_label = QLabel("Brightness")
        self.brigheness_panel.addWidget(self.brightness_label)
        self.brightness_slider = FloatSlider(decimals=0,direction = Qt.Horizontal)
        self.brightness_slider.setRange(-self.image_B-self.image_B*9,-self.image_B+self.image_B*9)
        self.brightness_slider.setValue(-self.image_B)  # Default brightness
        self.brightness_slider.valueChanged.connect(self.adjust_image)
        self.brigheness_panel.addWidget(self.brightness_slider)

        self.slider_panel.addSpacing(20)

        # Contrast slider
        self.contrast_panel = QVBoxLayout()
        self.slider_panel.addLayout(self.contrast_panel)
        self.contrast_label = QLabel("Contrast")
        self.contrast_panel.addWidget(self.contrast_label)
        self.contrast_slider = FloatSlider(decimals=5,direction = Qt.Horizontal)
        self.contrast_slider.setRange(0,self.image_C*10)
        self.contrast_slider.setValue(self.image_C*3)  # Default contrast
        self.contrast_slider.valueChanged.connect(self.adjust_image)
        self.contrast_panel.addWidget(self.contrast_slider)

        self.layout.addWidget(self.image_view)

        # Slider to switch between images in the stack
        self.image_slider = QSlider(Qt.Horizontal)
        self.image_slider.setTickPosition(QSlider.TicksBelow)
        self.image_slider.setTickInterval(1)
        self.image_slider.valueChanged.connect(self.update_image)
        self.num_images = len(self.image_stack)
        self.label = QLabel(f"Image {self.current_index + 1} / {self.num_images}")
        self.layout.addWidget(self.image_slider)
        self.layout.addWidget(self.label)
        
        self.setLayout(self.layout)
        #self.image_stack = None
        #self.current_image = None
        """Set a stack of images (numpy array) to be displayed."""
        self.image_slider.setMaximum(image_stack.shape[0] - 1)  # Set max value to number of images in the stack
        self.image_slider.setValue(0)  # Start with the first image
        self.current_image = self.image_stack[0].astype(np.float32)
        self.rectangle_mode = False
        self.circle_mode = False
        self.overlay_visible = True
        self.overlay_img = None
        self.overlay = np.zeros((self.width,self.height,4),dtype=np.uint8)
        self.auto_adjust()
        self.update_image()  # Show the first image
        # List to store current ROIs
        self.current_rois = []
        self.x_indices,self.y_indices = np.indices((self.width,self.height))
        self.set_auto_roi()

    def calculate_BC(self,np_image):
        """Calculate the best brightness and contrast for displaying a 16-bit image."""
        # 计算图像的最小和最大值
        min_val = np.min(np_image)
        max_val = np.max(np_image)

        # 计算最佳亮度（使用图像的中位数）
        brightness = np.median(np_image)

        # 计算最佳对比度（使用最大值和最小值的差）
        contrast = 1/(max_val - min_val)

        # 防止对比度为零
        if contrast == 0:
            contrast = -1  # 设置为1，以避免除以零

        self.image_B = brightness
        self.image_C = contrast

    def update_image(self):
        if self.image_stack is not None:
            index = self.image_slider.value()  # Get the current image index
            self.current_image = self.image_stack[index].astype(np.float32)
            self.adjust_image()  # Apply brightness/contrast adjustments to the selected image
            self.current_index = index
            self.label.setText(f"Image {self.current_index + 1} / {self.num_images}")

    def adjust_image(self):
        if self.current_image is not None:
            brightness = -self.brightness_slider.getFloatValue()
            contrast = self.contrast_slider.getFloatValue()
            #print(brightness,contrast)
            img_normalized = (self.current_image - brightness)*contrast
            #print(np.max(img_normalized))
            img_normalized = np.clip(img_normalized, 0, 1)
            img_8bit = (img_normalized * 255).astype(np.uint8)
            self.image_view.setImage(img_8bit, autoLevels=False)
            return img_8bit

    def auto_adjust(self):
        """Automatically adjust brightness and contrast based on image statistics."""
        if self.current_image is not None:
            np_image = self.current_image
            min_val = np.min(np_image)
            max_val = np.max(np_image)

            # 计算最佳亮度（使用图像的中位数）
            brightness = np.median(np_image)

            # 计算最佳对比度（使用最大值和最小值的差）
            contrast = 1/(max_val - min_val)

            # 防止对比度为零
            if contrast == 0:
                contrast = 1  # 设置为1，以避免除以零

            self.image_B = brightness
            self.image_C = contrast*3

            self.brightness_slider.setValue(-self.image_B)
            self.contrast_slider.setValue(self.image_C)
            # Apply the adjustments to the image
            img_8bit = self.adjust_image()
            self.image_view.setImage(img_8bit, autoLevels=True)

    def add_full_roi(self):
        self.image_view.removeItem(self.overlay_img)
        """Add a rectangular ROI to the image view."""
        self.clear_rois()  # Clear existing ROIs
        self.rectangle_mode = True
        self.circle_mode = False
        if self.current_image is not None:
            # Define ROI size and position ensuring it is within image boundaries
            width, height = self.width, self.height
            pos = [0,0]
            roi = pg.RectROI(pos, np.int32([width, height]), pen='r')  # Create a rectangular ROI

            self.image_view.addItem(roi)  # Add the ROI to the ImageView
            roi.setZValue(10)  # Bring the ROI to the front
            roi.translatable = False
            self.current_rois.append(roi)  # Store the added ROI
            for handle in roi.getHandles():
                roi.removeHandle(handle)
            self.roi_left = roi.pos().x()
            self.roi_right = roi.pos().x()+roi.size().x()
            self.roi_top = roi.pos().y()
            self.roi_bottom = roi.pos().y()+roi.size().y()
            self.roi_width = roi.size().x()
            self.roi_height = roi.size().y()

            #print(self.roi_left,self.roi_width)
            self.create_roi_mask()
            self.roi_image_init()
            # Constrain the ROI within the image boundaries during drag
            #roi.sigRegionChangeFinished.connect(lambda: self.constrain_roi(roi))
        self.overlay_visible = True
        self.toggle_roi_display()

    def add_rect_roi(self):
        self.image_view.removeItem(self.overlay_img)
        """Add a rectangular ROI to the image view."""
        self.clear_rois()  # Clear existing ROIs
        self.rectangle_mode = True
        self.circle_mode = False
        if self.current_image is not None:
            # Define ROI size and position ensuring it is within image boundaries
            width, height = self.width, self.height
            pos = np.int32([width/4, height/4])
            roi = pg.RectROI(pos, np.int32([width/2, height/2]), pen='r')  # rectangular ROI

            self.image_view.addItem(roi)  # Add the ROI to the ImageView
            roi.setZValue(10)  # Bring the ROI to the front
            self.current_rois.append(roi)  # Store the added ROI

            self.roi_left = roi.pos().x()
            self.roi_right = roi.pos().x()+roi.size().x()
            self.roi_top = roi.pos().y()
            self.roi_bottom = roi.pos().y()+roi.size().y()
            self.roi_width = roi.size().x()
            self.roi_height = roi.size().y()

            #print(self.roi_left,self.roi_width)

            # Constrain the ROI within the image boundaries during drag
            roi.sigRegionChangeFinished.connect(lambda: self.constrain_roi(roi))
            self.create_roi_mask()
            self.roi_image_init()
        self.overlay_visible = True
        self.toggle_roi_display()
        
    def add_circle_roi(self):
        self.image_view.removeItem(self.overlay_img)
        """Add a circular ROI to the image view."""
        self.clear_rois()  # Clear existing ROIs
        self.rectangle_mode = False
        self.circle_mode = True
        if self.current_image is not None:
            radius = int(self.width/2)  # Define the radius of the circular ROI
            # Define the center ensuring it is within image boundaries
            center = np.int32([self.width/4,self.height/4])
            roi = pg.CircleROI(center, radius, pen='g')  # Create a circular ROI

            self.image_view.addItem(roi)  # Add the circular ROI to the ImageView
            roi.setZValue(10)  # Bring the ROI to the front
            self.current_rois.append(roi)  # Store the added ROI

            self.roi_left = roi.pos().x()
            self.roi_right = roi.pos().x()+roi.size().x()
            self.roi_top = roi.pos().y()
            self.roi_bottom = roi.pos().y()+roi.size().y()
            self.roi_width = roi.size().x()
            self.roi_height = roi.size().y()
            # Constrain the ROI within the image boundaries during drag
            roi.sigRegionChangeFinished.connect(lambda: self.constrain_roi(roi))
            self.create_roi_mask()
            self.roi_image_init()
        self.overlay_visible = True
        self.toggle_roi_display()

    def set_auto_roi(self):
        self.clear_rois()
        self.circle_mode = False
        self.rectangle_mode = False
        self.create_roi_mask()
        self.roi_image_init()
        self.overlay_visible = False
        self.toggle_roi_display()

    def constrain_roi(self, roi):
        self.image_view.removeItem(self.overlay_img)
        self.overlay_visible = False
        """Constrain the ROI to stay within the image boundaries."""
        bounds = QRectF(0, 0, self.width, self.height)
        left = roi.pos().x()
        right = roi.pos().x()+roi.size().x()
        top = roi.pos().y()
        bottom = roi.pos().y()+roi.size().y()
        width = roi.size().x()
        height = roi.size().y()
        # Check if ROI is out of bounds and adjust position
        # 把这里的判断条件简化成只有一次，以节省时间
        if width > self.width:
            roi.setSize(self.width,roi.size().y())
        if height > self.height:
            roi.setSize(roi.size().x(),height)
        if left < bounds.left():
            roi.setPos(bounds.left(), roi.pos().y())
        if top < bounds.top():
            roi.setPos(roi.pos().x(), bounds.top())
        if right > bounds.right():
            roi.setPos(bounds.right() - width, roi.pos().y())
        if bottom > bounds.bottom():
            roi.setPos(roi.pos().x(), bounds.bottom() - height)
        #print(left,right,top,bottom)
        self.roi_left = roi.pos().x()
        self.roi_right = roi.pos().x()+roi.size().x()
        self.roi_top = roi.pos().y()
        self.roi_bottom = roi.pos().y()+roi.size().y()
        self.roi_width = roi.size().x()
        self.roi_height = roi.size().y()
        #print(self.create_roi_mask())
        self.create_roi_mask()
        self.roi_image_init()

    def clear_rois(self):
        """Clear all existing ROIs."""
        for roi in self.current_rois:
            self.image_view.removeItem(roi)  # Remove the ROI from the image view
        self.current_rois.clear()  # Clear the list of current ROIs

    def create_roi_mask(self):
        image_shape = np.array([self.width,self.height])
        # Initialize a mask of zeros with the same height and width as the image
        mask = np.zeros(image_shape, dtype=np.uint8)
        if len(self.current_rois)>0:
            if self.rectangle_mode == True:
                # Get the coordinates of the ROI
                x_start = int(self.roi_left)
                y_start = int(self.roi_top)
                x_end = int(self.roi_right)  # width
                y_end = int(self.roi_bottom)  # height
                #print(x_start,x_end,y_start,y_end)
                # Set the ROI area to 1s
                mask[x_start:x_end,y_start:y_end] = 1
            elif self.circle_mode == True:
                center_x = (self.roi_left+self.roi_right)/2
                center_y = (self.roi_top+self.roi_bottom)/2
                radius_x = (self.roi_right-self.roi_left)/2
                radius_y = (self.roi_bottom-self.roi_top)/2
                distances_squared = (self.x_indices-center_x)**2 + (self.y_indices-center_y)**2
                mask[distances_squared <= radius_x**2/2+radius_y**2/2] = 1
        else:
            print('auto')
            mask = self.roi_mask_auto
        self.mask = mask
        #print(self.mask.T)
        data_extract_mask(self.image_stack,self.mask)
        return self.mask.T

    def roi_image_init(self):
        self.overlay = np.zeros((self.width,self.height,4),dtype=np.uint8)
        if self.overlay_img:
            self.image_view.removeItem(self.overlay_img)
        if self.rectangle_mode == False and self.circle_mode == False:
            roi = self.roi_mask_auto
        else:
            roi = self.mask
        #print(roi)
        self.overlay[roi==1,0] = 255
        self.overlay[roi==1,3] = 128

    def toggle_roi_display(self):
        if self.overlay_img:
            self.image_view.removeItem(self.overlay_img)
        self.overlay_visible = not self.overlay_visible
        #print(np.max(self.roi_mask_auto),self.roi_mask_auto.shape)
        self.overlay_img = pg.ImageItem(self.overlay)
        self.image_view.addItem(self.overlay_img)
        self.overlay_img.setVisible(self.overlay_visible)
        #print('toggle!')

class TiffImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        #self.image_B,self.image_C = self.calculate_BC(image_stack[0])
        #print(self.image_B,self.image_C)
        #self.current_index = 0
        #self.num_images = image_stack.shape[0]
        #self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def image_show(self,image_stack, roi_mask):
        # Create layout
        self.image_stack = image_stack
        self.roi_mask = roi_mask
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Create a QLabel to display images
        #self.image_label = ImageLabel(self)
        self.image_label = ImageAdjustWidget(self.image_stack,self.roi_mask)
        #self.image_label.setMinimumSize(500, 500)
        #self.image_label.setMaximumSize(500, 500)
        #self.setFixedWidth(500)
        #self.setMinimumWidth(500)
        #self.setMinimumHeight(580)

        # Create a slider to navigate through the stack
        #self.slider = QSlider(Qt.Horizontal)
        #self.slider.setMinimum(0)
        #self.slider.setMaximum(self.num_images - 1)
        #self.slider.setValue(0)
        #self.slider.setTickPosition(QSlider.TicksBelow)
        #self.slider.setTickInterval(1)
        #self.slider.valueChanged.connect(self.update_image)

        # Label to display current index
        #self.label = QLabel(f"Image {self.current_index + 1} / {self.num_images}")

        # Create buttons for resetting and allowing ROI selection
        button_layout = QHBoxLayout()

        self.auto_roi_button = QPushButton("Auto Mask")
        self.auto_roi_button.clicked.connect(self.image_label.set_auto_roi)
        button_layout.addWidget(self.auto_roi_button)

        self.full_roi_button = QPushButton("Select Full")
        self.full_roi_button.clicked.connect(self.image_label.add_full_roi)
        button_layout.addWidget(self.full_roi_button)

        self.rectangle_roi_button = QPushButton("Select Rectangle")
        self.rectangle_roi_button.clicked.connect(self.image_label.add_rect_roi)
        button_layout.addWidget(self.rectangle_roi_button)

        self.circle_roi_button = QPushButton("Select Circle")
        self.circle_roi_button.clicked.connect(self.image_label.add_circle_roi)
        button_layout.addWidget(self.circle_roi_button)

        self.toggle_roi_button = QPushButton("Toggle ROI")
        self.toggle_roi_button.clicked.connect(self.image_label.toggle_roi_display)
        button_layout.addWidget(self.toggle_roi_button)

        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.image_label)

class FloatSlider(QSlider):
    def __init__(self, decimals=2, direction = Qt.Vertical,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factor = 10 ** decimals  # 乘数因子，用于转换小数
        self._min_value = 0
        self._max_value = 1
        self.setOrientation(direction)
        self.valueChanged.connect(self._update_value)

    def _update_value(self):
        # 内部函数，将值转换回小数
        value = self.value() / self._factor
        self.float_value = value  # 存储转换后的小数值
    
    def setRange(self, min_value, max_value):
        """Override setRange to work with floating-point numbers."""
        self._min_value = min_value
        self._max_value = max_value
        super().setRange(int(min_value * self._factor), int(max_value * self._factor))

    def setValue(self, value):
        """Override setValue to work with floating-point numbers."""
        super().setValue(int(value * self._factor))

    def getFloatValue(self):
        """Get the current floating-point value of the slider."""
        return self.float_value

def create_rotated_label(text,degree):
    # 创建 QGraphicsView 和 QGraphicsScene
    view = QGraphicsView()
    scene = QGraphicsScene(view)

    # 创建 QGraphicsTextItem 并设置文本
    text_item = QGraphicsTextItem(text)
    text_item.setRotation(degree)  # 逆时针旋转90度
    scene.addItem(text_item)
    view.setScene(scene)
    view.setBackgroundBrush(Qt.transparent)
    #view.setFrameShape(QGraphicsView.NoFrame)
    view.setFixedWidth(30)  # 设置固定大小以适应旋转的文本
    return view

def plot_slider_data(canvas, x, y, title, label, drift, faraday):
    # Apply the compensations and normalization (assuming slider_compensate and slider_normalize are defined)
    x_plot, y_plot = slider_compensate(x, y, drift, faraday)
    x_plot, y_plot = slider_normalize(x_plot, y_plot)

    # Ensure that the data loops back for a closed plot (if this is your goal)
    x_plot = np.r_[x_plot, [x_plot[0]]]
    y_plot = np.r_[y_plot, [y_plot[0]]]

    # Clear the previous plot
    canvas.clear()

    # Plot the new data on the canvas using pyqtgraph's plot function
    canvas.plot(x_plot, y_plot, pen='#1F77B4', width=5, name=label)

    # Set plot title and limits
    canvas.plotItem = canvas.getPlotItem()
    canvas.plotItem.setTitle(title)
    ylim = max(y_plot)
    canvas.plotItem.setYRange(-ylim * 1.2, ylim * 1.4)
    canvas.setBackground('w')
    canvas.plotItem.setLabel('bottom', 'Magnetic Field', color='k', units='mT')
    canvas.plotItem.setLabel('left', 'MOKE Signal', color='k', units='a.u.')
    canvas.plotItem.addLegend()
    canvas.plotItem.showGrid(x=True, y=True)
    canvas.plotItem.getAxis('bottom').setTextPen('k')  # Bottom axis label color (black)
    canvas.plotItem.getAxis('left').setTextPen('k')
    # Optionally, you can set the labels (already set in the `PGCanvas` class)
    canvas.plotItem.setLabel('bottom', 'Magnetic Field', units='mT')
    canvas.plotItem.setLabel('left', 'MOKE Signal', units='a.u.')

    # Return the y_plot for further use
    return y_plot

def center(data_x,data_y):
    length = len(data_x)
    max_x = max(data_x)
    min_x = min(data_x)
    fit_range = 0.5#Absolute,mT
    level_range = 0.5#Absolute,mT
    fit_range = max(0.1*length,3)#Relative
    level_range = max(0.1*length,3)#Relative
    data_fit_x_1 = []
    data_fit_y_1 = []
    data_fit_x_2 = []
    data_fit_y_2 = []
    y_raw = data_y
    ###Remove Drift
    drift = data_y[-1]-2*data_y[0]+data_y[1]
    slope = drift/length
    #print(slope)
    data_y = data_y-slope*range(length)

    ###Remove Faraday Effect
    #for i in range(length):#Absolute
    #    if data_x[i]<-fit_range:
    #        data_fit_x_1.append(data_x[i])
    #        data_fit_y_1.append(data_y[i])
    #    elif data_x[i]>fit_range:
    #        data_fit_x_2.append(data_x[i])
    #        data_fit_y_2.append(data_y[i])
    for i in range(length):#Relative
        if abs(i-length/4)<fit_range:
            data_fit_x_1.append(data_x[i])
            data_fit_y_1.append(data_y[i])
        elif abs(i-length*3/4)<fit_range:
            data_fit_x_2.append(data_x[i])
            data_fit_y_2.append(data_y[i])
    #print(data_fit_x_1,data_fit_x_2)
    factor_1 = np.polyfit(data_fit_x_1,data_fit_y_1,1)
    factor_2 = np.polyfit(data_fit_x_2,data_fit_y_2,1)
    fit_slope, fit_intercept = (factor_1+factor_2)/2
    #print(fit_slope,fit_intercept)
    data_y = data_y-fit_slope*data_x-fit_intercept

    ###Normalization
    plane_1 = []
    plane_2 = []
    for i in range(length):
        if abs(i-length/4)<level_range:
            plane_1.append(data_y[i])
        if abs(i-length*3/4)<level_range:
            plane_2.append(data_y[i])
    plain_1 = np.average(plane_1)
    plain_2 = np.average(plane_2)
    data_y = ((data_y-min(plain_1,plain_2))/abs(plain_1-plain_2)*2-1)
    #print(len(data_x),len(data_y),len(y_raw))
    return data_x,data_y,slope,fit_slope,y_raw

def slider_compensate(data_x,data_y,drift,faraday):
    length = len(data_x)
    data_y = data_y-drift*np.arange(length)
    data_y = data_y-faraday*data_x
    return data_x,data_y

def slider_normalize(data_x,data_y):
    length = len(data_x)
    level_range = 0.5#Absolute,mT
    level_range = max(0.1*length,3)#Relative
    ###Normalization
    plane_1 = []
    plane_2 = []
    for i in range(length):
        if abs(i-length/4)<level_range:
            plane_1.append(data_y[i])
        if abs(i-length*3/4)<level_range:
            plane_2.append(data_y[i])
    plain_1 = np.average(plane_1)
    plain_2 = np.average(plane_2)
    #print(plain_1,plain_2)
    data_y = (data_y-min(plain_1,plain_2))/abs(plain_1-plain_2)*2-1
    return data_x,data_y

def data_extract(file_in_name):
    #Extract raw data and calculate the averaged images
    with h5py.File(file_in_name,'r') as file_in:
        print('\nLoading '+file_in_name)
        loop_number = int(file_in['steps_experiment/info'].attrs['n_loops'])-int(file_in['steps_experiment/info'].attrs['skip_loops'])
        print(str(loop_number)+' loop(s) detected!')
        data = list(file_in['steps_experiment/data/steps'])
        data_count = []
        for i in data:
            data_count.append(int(i[0::]))
        #print(data_count)
        min_DC,max_DC = min(data_count),max(data_count)
        data_number = len(data_count)
        data_1_number = int(data_number/loop_number)
        data_name = []
        for i in range(min_DC,max_DC+1):
            data_name.append(''+str(i))
        #print(data_name)
        field = []
        j = 0
        for i in range(min_DC,min_DC+data_1_number):
            field_path = 'steps_experiment/data/steps/'+data_name[j]
            #print(field_path)
            field.append(file_in[field_path].attrs['target_signal'].round(5))
            j += 1
        field = np.array(field)
        #print(field)
        MOKE_type = np.argmax(field[int(data_1_number/4)])
        if MOKE_type == 0:
            label = 'B_x'
        elif MOKE_type == 1:
            label = 'B_y'
        else:
            label = 'B_z'
        print(label+' was applied')

        signal = np.zeros((data_1_number,loop_number,2))
        #print(signal.shape)
        data_path = 'steps_experiment/data/steps/'+data_name[0]+'/image_data'
        image_data = np.array(file_in[data_path])
        image_width = image_data.shape[0]#???
        image_height = image_data.shape[1]#???
        image_stack = np.zeros((data_1_number,loop_number+1,image_width,image_height))
        print('Processing Images:')
        for i in range(loop_number):
            #image_stack = []
            for j in range(data_1_number):
                k = data_1_number*i+j
                c = ((k+1)/data_number)*100
                a = '*'*round(c*50/100)
                b = '.'*round(50-c*50/100)
                print('\r{:^3.0f}%[{}->{}]'.format(c,a,b),end = '')
                data_path = 'steps_experiment/data/steps/'+data_name[k]+'/image_data'
                image_data = np.array(file_in[data_path])
                #print(image_data)
                #image_stack.append(image_data)
                image_stack[j,i,:,:] = image_data
                signal[j,i,0] = np.average(image_data)
                signal[j,i,1] = 1#signal[j,i,0]/signal[j,0,0]#!!!
            stack_name = file_in_name.replace('.h5','_loop'+str(i+1).zfill(3))+'.tif'
            image_stack_out = (np.array(image_stack[:,i,:,:])).astype(np.uint16)
            #print(image_stack_out.shape)
            #print(image_stack_out[0])
            imwrite(stack_name,image_stack_out,photometric='MINISBLACK')
        #print(signal)

    #normalize image data into 1st loop
    print('\nNormalizing Images:')
    for j in range(data_1_number):
        image_ave = np.zeros((image_width,image_height))
        for i in range(loop_number):
            image_ave += image_stack[j,i,:,:]*signal[j,i,1]
        #print(loop_number)
        k = j
        c = ((k+1)/data_1_number)*100
        a = '*'*round(c*50/100)
        b = '.'*round(50-c*50/100)
        print('\r{:^3.0f}%[{}->{}]'.format(c,a,b),end = '')
        image_stack[j,loop_number,:,:] = image_ave/loop_number
    print('\n')
    image_stack_ave = (np.array(image_stack[:,loop_number,:,:])).astype(np.uint16)
    image_ave = np.average(image_stack_ave,axis = 0).astype(np.uint16)
    imwrite(file_in_name.replace('.h5','_ave')+'.tif',image_ave,photometric='MINISBLACK')
    roi_mask,threshold = auto_threshold(image_ave)
    imwrite(file_in_name.replace('.h5','_mask')+'.tif',roi_mask,photometric='MINISBLACK')
    #print(roi_mask,threshold)

    data_out = np.zeros((data_1_number,loop_number+5))
    data_out[:,0:3] = field[:,0:3]
    data_out[:,3:3+loop_number] = signal[:,0:loop_number,0]
    data_out[:,-2] = np.average(signal[:,0:loop_number,0],axis=1)
    #print(data_out)
    return data_out,image_stack_ave,roi_mask,image_stack_ave*roi_mask


#这里考虑变成多线程，返回值有了以后再刷新
def data_extract_mask(image_stack,mask):
    #print(image_stack.shape)
    width = image_stack[0].shape[0]
    height = image_stack[0].shape[1]
    image_stack_masked = image_stack*mask
    mean_value = image_stack_masked.mean(axis=(1, 2))/mask.sum()*width*height
    print(mean_value)


def auto_threshold(image):
    # 初始化阈值为图像像素值的均值
    threshold = np.mean(image)
    
    while True:
        # 将图像划分为两个区域：小于阈值的为背景，大于阈值的为前景
        foreground = image[image > threshold]
        background = image[image <= threshold]

        # 计算前景和背景的均值
        if len(foreground) == 0 or len(background) == 0:
            break
        
        foreground_mean = np.mean(foreground)
        background_mean = np.mean(background)
        
        # 计算新的阈值
        new_threshold = (foreground_mean + background_mean) / 2
        
        # 如果新旧阈值之间的差异很小，说明已收敛，结束迭代
        if abs(new_threshold - threshold) < 0.5:
            break
        
        threshold = new_threshold  # 更新阈值

    # 生成二值化的mask：亮区为1，暗区为0
    mask = np.zeros_like(image)
    mask[image > threshold] = 1
    return mask, threshold


def data_plot_default(file_in_name,data_out,window):
    plt.rcParams["figure.figsize"] = (3,3)
    plt.rcParams['figure.constrained_layout.use'] = True
    MOKE_type = np.argmax(data_out[int(len(data_out)/4),0:3])
    if MOKE_type == 0:
        label = 'B_x'
    elif MOKE_type == 1:
        label = 'B_y'
    else:
        label = 'B_z'
    data_out[:,MOKE_type],data_out[:,-1],_,_,_ = center(data_out[:,MOKE_type],data_out[:,-2])
    data_out = np.r_[data_out,[data_out[0]]]
    loop_number = len(data_out[0])-5
    #plt.plot(data_out[:,0],data_out[:,1])
    plt.figure('Default')
    plt.cla()
    plt.plot(data_out[:,MOKE_type],data_out[:,-1],label=label)
    plt.title(file_in_name.split('/')[-1])
    plt.legend(loc='upper left')
    ylim = max(data_out[:,-1])
    plt.ylim(-ylim*1.2,ylim*1.4)
    plt.xlabel('Magnetic Field (mT)')
    plt.ylabel('MOKE Signal (a.u.)')
    plt.savefig(file_in_name.replace('.h5','.png'),bbox_inches = 'tight',dpi=400)
    plt.close()
    with open(file_in_name.replace('.h5','.dat'),'w') as file_out:
        file_out.write('#field_x\t#field_y\t#field_z\t'+'#signal\t'*loop_number+'#Signal_ave\t#Signal_norm\n')
        np.savetxt(file_out,data_out,delimiter='\t',fmt='%.6f')
    run_default_loop(window)

def data_save_default(file_in_name,data_out,drift,faraday):
    plt.rcParams["figure.figsize"] = (3,3)
    plt.rcParams['figure.constrained_layout.use'] = True
    MOKE_type = np.argmax(data_out[int(len(data_out)/4),0:3])
    if MOKE_type == 0:
        label = 'B_x'
    elif MOKE_type == 1:
        label = 'B_y'
    else:
        label = 'B_z'
    x = data_out[:,MOKE_type]
    y = data_out[:,-2]
    x_plot,y_plot = slider_compensate(x,y,drift,faraday)
    x_plot,y_plot = slider_normalize(x_plot,y_plot)
    data_out[:,-1] = y_plot
    data_out = np.r_[data_out,[data_out[0]]]
    loop_number = len(data_out[0])-5
    plt.figure('Slider')
    plt.cla()
    plt.plot(data_out[:,MOKE_type],data_out[:,-1],label=label)
    plt.title(file_in_name.split('/')[-1])
    plt.legend(loc='upper left')
    ylim = max(data_out[:,-1])
    plt.ylim(-ylim*1.2,ylim*1.4)
    plt.xlabel('Magnetic Field (mT)')
    plt.ylabel('MOKE Signal (a.u.)')
    plt.savefig(file_in_name.replace('.h5','.png'),bbox_inches = 'tight',dpi=400)
    plt.close()
    with open(file_in_name.replace('.h5','.dat'),'w') as file_out:
        file_out.write('#field_x\t#field_y\t#field_z\t'+'#signal\t'*loop_number+'#Signal_ave\t#Signal_norm\n')
        np.savetxt(file_out,data_out,delimiter='\t',fmt='%.6f')

def data_plot_slider(file_in_name,data_out):
    MOKE_type = np.argmax(data_out[int(len(data_out)/4),0:3])
    if MOKE_type == 0:
        label = 'B_x'
    elif MOKE_type == 1:
        label = 'B_y'
    else:
        label = 'B_z'
    data_out[:,MOKE_type],data_out[:,-1],drift,faraday,y_raw = center(data_out[:,MOKE_type],data_out[:,-2])
    #data_out = np.r_[data_out,[data_out[0]]]
    #plt.plot(data_out[:,0],data_out[:,1])
    x = data_out[:,MOKE_type]
    y = data_out[:,-1]
    title = file_in_name.split('/')[-1]
    #print(len(x),len(y),len(y_raw))
    return x,y,title,label,drift,faraday,y_raw,data_out

def data_save_slider(file_in_name,data_out,drift,faraday):
    plt.rcParams["figure.figsize"] = (3,3)
    plt.rcParams['figure.constrained_layout.use'] = True
    MOKE_type = np.argmax(data_out[int(len(data_out)/4),0:3])
    if MOKE_type == 0:
        label = 'B_x'
    elif MOKE_type == 1:
        label = 'B_y'
    else:
        label = 'B_z'
    x = data_out[:,MOKE_type]
    y = data_out[:,-2]
    x_plot,y_plot = slider_compensate(x,y,drift,faraday)
    x_plot,y_plot = slider_normalize(x_plot,y_plot)
    data_out[:,-1] = y_plot
    data_out = np.r_[data_out,[data_out[0]]]
    loop_number = len(data_out[0])-5
    plt.figure('Slider')
    plt.cla()
    plt.plot(data_out[:,MOKE_type],data_out[:,-1],label=label)
    plt.title(file_in_name.split('/')[-1])
    plt.legend(loc='upper left')
    ylim = max(data_out[:,-1])
    plt.ylim(-ylim*1.2,ylim*1.4)
    plt.xlabel('Magnetic Field (mT)')
    plt.ylabel('MOKE Signal (a.u.)')
    plt.savefig(file_in_name.replace('.h5','.png'),bbox_inches = 'tight',dpi=400)
    plt.close()
    with open(file_in_name.replace('.h5','.dat'),'w') as file_out:
        file_out.write('#field_x\t#field_y\t#field_z\t'+'#signal\t'*loop_number+'#Signal_ave\t#Signal_norm\n')
        np.savetxt(file_out,data_out,delimiter='\t',fmt='%.6f')

def run_default_loop(window):
    finished = pyqtSignal()
    if window.step < len(window.file_list):
        file = window.file_list[window.step]
        window.analyzing_default = Analyzing_default(file,window)
        window.analyzing_default.start()
        window.analyzing_default.finished.connect(data_plot_default)
        window.step += 1
    else:
        print('Done!')
        window.close()

class Analyzing_default(QThread):
    finished = pyqtSignal(str,np.ndarray,object)
    def __init__(self,file,window):
        super().__init__()
        self.file = file
        self.window = window
        print(file)
    def run(self):
        try:
            print("Start Processing...")
            data_out,_,_,_ = data_extract(self.file)
            #print(self.file)
            self.finished.emit(self.file,data_out,self.window)
        except:
            print('Failed!')

def run_slider_loop(window):
    if window.step > 0:
        data_save_slider(window.file_list[window.step-1],window.data_out,window.drift,window.faraday)
    if window.step < len(window.file_list):
        file = window.file_list[window.step]
        #print(window.file_list)
        window.analyzing_slider = Analyzing_slider(file,window.canvas)
        window.analyzing_slider.data_ready.connect(plot_slider_data)
        window.analyzing_slider.finished.connect(window.initialize_slider)
        window.analyzing_slider.start()
        if window.step == len(window.file_list)-1:
            window.save_button.setText('Save && Exit')
        window.step += 1
    else:
        window.save_button.setEnabled(False)
        window.close()

class Analyzing_slider(QThread):
    finished = pyqtSignal(np.ndarray,np.ndarray,str,str,float,float,np.ndarray,np.ndarray,np.ndarray,np.ndarray)
    data_ready = pyqtSignal(object,np.ndarray,np.ndarray,str,str,float,float)
    def __init__(self,file,canvas):
        super().__init__()
        self.file = file
        self.canvas = canvas
        print(file)
    def run(self):
        print("Start Processing...")
        file = self.file
        canvas = self.canvas
        #print(file)
        x,y,title,label,drift,faraday,y_raw,data_out,image_stack_ave,roi_mask,image_stack_masked = analyze_slider(file)
        self.finished.emit(x,y_raw,title,label,drift,faraday,data_out,image_stack_ave,roi_mask,image_stack_masked)
        self.data_ready.emit(canvas,x,y_raw,title,label,drift,faraday)

def analyze_slider(file):
    #print(files)
    if '.h5' in file:
        file_in_name = file
        print("Processing " + file)
        try:
            data_out,image_stack_ave,roi_mask,image_stack_masked = data_extract(file_in_name)
            x,y,title,label,drift,faraday,y_raw,data_out = data_plot_slider(file_in_name,data_out)
            return x,y,title,label,drift,faraday,y_raw,data_out,image_stack_ave,roi_mask,image_stack_masked
        except:
            print('Failed!')
    print('Done!')

class Analyzing_mask(QThread):
    def __init__(self,data_out,image_stack_masked,roi_mask):
        super().__init__()
        self.data_out = data_out
        self.image_stack_masked = image_stack_masked
        self.roi_mask = roi_mask
    def run(self):
        print(self.roi_mask)