import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QSlider, QWidget, QVBoxLayout, QLabel
import h5py
import math as m
import numpy as np
from tifffile import imwrite


class FloatSlider(QSlider):
    def __init__(self, decimals=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factor = 10 ** decimals  # 乘数因子，用于转换小数
        self._min_value = 0
        self._max_value = 1
        self.setOrientation(Qt.Vertical)
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


def plot_slider_data(canvas, x, y, title, label, drift, faraday):
    import numpy as np
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

    canvas.setBackground('w')
    canvas.plotItem = canvas.getPlotItem()
    canvas.plotItem.setLabel('bottom', 'Magnetic Field', color='k', units='mT')
    canvas.plotItem.setLabel('left', 'MOKE Signal', color='k', units='a.u.')
    canvas.plotItem.addLegend()
    canvas.plotItem.showGrid(x=True, y=True)
    canvas.plotItem.getAxis('bottom').setTextPen('k')  # Bottom axis label color (black)
    canvas.plotItem.getAxis('left').setTextPen('k')

    # Set plot title and limits
    canvas.plotItem.setTitle(title)
    ylim = max(y_plot)
    canvas.plotItem.setYRange(-ylim * 1.2, ylim * 1.4)

    # Optionally, you can set the labels (already set in the `PGCanvas` class)
    canvas.plotItem.setLabel('bottom', 'Magnetic Field', units='mT')
    canvas.plotItem.setLabel('left', 'MOKE Signal', units='a.u.')

    # Return the y_plot for further use
    return y_plot


def center(data_x,data_y):
    import numpy as np
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
    import numpy as np
    length = len(data_x)
    data_y = data_y-drift*np.arange(length)
    data_y = data_y-faraday*data_x
    return data_x,data_y


def slider_normalize(data_x,data_y):
    import numpy as np
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

        signal = np.zeros((data_1_number,loop_number))
        #print(signal.shape)
        print('Processing Images:')
        for i in range(loop_number):
            image_stack = []
            for j in range(data_1_number):
                k = data_1_number*i+j
                c = ((k+1)/data_number)*100
                a = '*'*round(c*50/100)
                b = '.'*round(50-c*50/100)
                print('\r{:^3.0f}%[{}->{}]'.format(c,a,b),end = '')
                data_path = 'steps_experiment/data/steps/'+data_name[k]+'/image_data'
                image_data = np.array(file_in[data_path])
                #print(image_data)
                image_stack.append(image_data)
                signal[j,i] = np.average(image_data)
            stack_name = file_in_name.replace('.h5','_loop'+str(i+1).zfill(3))+'.tif'
            image_stack = (np.array(image_stack)).astype(np.uint16)
            #print(image_stack.shape)
            #print(image_stack[0])
            imwrite(stack_name,image_stack,photometric='MINISBLACK')
        #print(signal)
        print('\n')

    data_out = np.zeros((data_1_number,loop_number+5))
    data_out[:,0:3] = field[:,0:3]
    data_out[:,3:3+loop_number] = signal[:,0:loop_number]
    data_out[:,-2] = np.average(signal[:,0:loop_number],axis=1)
    #print(data_out)
    return data_out


def data_plot_default(file_in_name,data_out,window):
    import numpy as np
    import matplotlib.pyplot as plt
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
    import numpy as np
    import matplotlib.pyplot as plt
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
    import numpy as np
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
    import numpy as np
    import matplotlib.pyplot as plt
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
        print("Start Processing...")
        data_out = data_extract(self.file)
        #print(self.file)
        self.finished.emit(self.file,data_out,self.window)


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
    import numpy as np
    finished = pyqtSignal(np.ndarray,np.ndarray,str,str,float,float,np.ndarray)
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
        x,y,title,label,drift,faraday,y_raw,data_out = analyze_slider(file)
        self.finished.emit(x,y_raw,title,label,drift,faraday,data_out)
        self.data_ready.emit(canvas,x,y_raw,title,label,drift,faraday)

def analyze_slider(file):
    #print(files)
    if '.h5' in file:
        file_in_name = file
        print("Processing " + file)
        try:
            data_out = data_extract(file_in_name)
            x,y,title,label,drift,faraday,y_raw,data_out = data_plot_slider(file_in_name,data_out)
            return x,y,title,label,drift,faraday,y_raw,data_out
        except:
            print('Failed!')
    print('Done!')