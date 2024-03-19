#!/usr/bin/env python
# coding: utf-8

# # Keras learning of simple simulated magnet

# #### Import the necessary modules

# In[1]:


get_ipython().run_line_magic('matplotlib', 'ipympl')
import numpy as np
from math import factorial
import matplotlib.pyplot as plt
import time
import tensorflow as tf
import keras as ks

import sys
sys.path.insert(0, '../Magnet_simulation/')
from virtual_magnet import magnet_response

from keras.layers import Input, Dense, Conv1D, GaussianNoise,BatchNormalization
from keras.optimizers import sgd
from keras import optimizers
from keras.models import Model
import keras.backend as K


# #### Get or create data

# In[37]:


N_sets = 4096*128
Set_size = 400
FFT_size = int(Set_size/2+1)
Max_time = 1
Renorm = 1

dt = Max_time/Set_size

r1 = np.random.rand(N_sets,) *2*np.pi

training_x = np.empty([N_sets, FFT_size])  # List of input numpy arrays
# training will consist of one vector:
# time vector from 0 to r1 in 25000 steps
training_y = np.empty([N_sets, FFT_size])
#  target output will consist of two vectors, one will be a sine wave with amplitude sqrt(r2)/r1

try:
    training_x = np.load('training_x.npy')
    training_y = np.load('training_y.npy')
    testing_x = np.load('testing_x.npy')
    testing_y = np.load('testing_y.npy')
except:
    for idx, item in enumerate(r1):
        print(idx/N_sets)
        t_vector = np.linspace(0, Max_time, Set_size)

        A1 = np.random.normal(0.15, 0.15)
        A2 = np.random.normal(0.15, 0.15)
        A3 = np.random.normal(0.15, 0.15)
        A4 = np.random.normal(0.15, 0.15)

        F1 = np.random.normal(10, 5)
        F2 = np.random.normal(20, 15)
        F3 = np.random.normal(40, 25)
        F4 = np.random.normal(200, 150)

        P1 = np.random.normal(np.pi, np.pi)
        P2 = np.random.normal(np.pi, np.pi)
        P3 = np.random.normal(np.pi, np.pi)
        P4 = np.random.normal(np.pi, np.pi)

        NI_signal = A1 * np.sin(2 * np.pi * F1 * t_vector + F1) + A2 * np.sin(2 * np.pi * F2 * t_vector + F2) + A3 * np.sin(2 * np.pi * F3 * t_vector + F3) + A4 * np.sin(2 * np.pi * F4 * t_vector + F4)
        H_signal = magnet_response(dt, NI_signal)

        training_x[idx, :] = np.abs(np.fft.rfft(H_signal))/Renorm/FFT_size
        training_y[idx, :] = np.abs(np.fft.rfft(NI_signal))/Renorm/FFT_size

    np.save('training_x.npy', training_x)
    np.save('training_y.npy', training_y)

    testing_x = np.empty([300, FFT_size])  # List of input numpy arrays
    testing_y = np.empty([300, FFT_size])

    for idx, item in enumerate(testing_x):
        t_vector = np.linspace(0, Max_time, Set_size)

        A1 = np.random.normal(0.15, 0.15)
        A2 = np.random.normal(0.15, 0.15)
        A3 = np.random.normal(0.15, 0.15)
        A4 = np.random.normal(0.15, 0.15)

        F1 = np.random.normal(10, 5)
        F2 = np.random.normal(20, 15)
        F3 = np.random.normal(40, 25)
        F4 = np.random.normal(200, 150)

        P1 = np.random.normal(np.pi, np.pi)
        P2 = np.random.normal(np.pi, np.pi)
        P3 = np.random.normal(np.pi, np.pi)
        P4 = np.random.normal(np.pi, np.pi)

        NI_signal = A1 * np.sin(2 * np.pi * F1 * t_vector + F1) + A2 * np.sin(2 * np.pi * F2 * t_vector + F2) + A3 * np.sin(
            2 * np.pi * F3 * t_vector + F3) + A4 * np.sin(2 * np.pi * F4 * t_vector + F4)
        H_signal = magnet_response(dt, NI_signal)

        testing_x[idx, :] = np.abs(np.fft.rfft(H_signal))/Renorm/FFT_size
        testing_y[idx, :] = np.abs(np.fft.rfft(NI_signal))/Renorm/FFT_size

    np.save('testing_x.npy', testing_x)
    np.save('testing_y.npy', testing_y)

print('Acquired data!')


# #### Create the model

# In[43]:


# This returns a tensor
inputs = Input((FFT_size,))
print(inputs.shape)
print(training_x.shape)
print(training_y.shape)

x = BatchNormalization()(inputs)
x = ks.layers.Reshape((1, FFT_size))(x)
for i in range(5):
    x = Conv1D(FFT_size, 1, activation='relu')(x)
x = Dense(FFT_size, activation='relu', use_bias=True)(x)
x = Dense(FFT_size, activation='relu', use_bias=True)(x)
predictions = ks.layers.Reshape((FFT_size,))(Dense(FFT_size, activation='relu', use_bias=True)(x))
print(predictions.shape)

def pow_diff(y_true, y_pred):
    return K.mean(K.pow((y_true - y_pred)*100,2)*(100*y_true+1))


model = Model(inputs=inputs, outputs=predictions)
optimizer_1 = optimizers.RMSprop(lr=0.001, rho=0.9, epsilon=None, decay=0.0)
optimizer_2 = ks.optimizers.Adagrad(lr=0.001, epsilon=None, decay=0.0)
model.compile(loss=pow_diff, optimizer='adam',metrics=['accuracy'])


# #### Prepare live plotting

# In[44]:


# Live loss plotting
from matplotlib import pyplot as plt
from IPython.display import clear_output
import time
plt.ion()

class PlotLearning(ks.callbacks.Callback):

    def on_train_begin(self, logs={}):
        
#         self.fig = plt.figure()
        self.i = 0
        self.x = []
        self.losses = []
        self.val_losses = []
        self.acc = []
        self.val_acc = []
        f, (ax1, ax2) = plt.subplots(1, 2, sharex=True)
        self.fig = f
        self.ax1 = ax1
        self.ax2 = ax2
        self.logs = []

    def on_epoch_end(self, epoch, logs={}):

        self.logs.append(logs)
        self.x.append(self.i)
        self.losses.append(logs.get('loss'))
        self.val_losses.append(logs.get('val_loss'))
        self.acc.append(logs.get('acc'))
        self.val_acc.append(logs.get('val_acc'))
        self.i += 1


#         clear_output(wait=True)

        self.ax1.clear()
        self.ax1.set_yscale('log')
        self.ax1.plot(self.x, self.losses, label="loss")
        self.ax1.plot(self.x, self.val_losses, label="val_loss")
        self.ax1.legend()

        self.ax2.clear()
        self.ax2.plot(self.x, self.acc, label="accuracy")
        self.ax2.plot(self.x, self.val_acc, label="validation accuracy")
        self.ax2.legend()
        plt.ylim(0, 1)

        self.fig.canvas.draw()
        plt.show()
        time.sleep(0.0001)
#         self.fig.canvas.draw()
#         plt.pause(0.001)

plot_losses = PlotLearning()


# #### Fit the model

# In[45]:


epochs = 100
for i in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]:
    model.fit(training_x, training_y, verbose=1, epochs=i*epochs, batch_size=1000,validation_data=(testing_x, testing_y))  # starts training
    model.save('RMS_loss_peaks_'+str(factorial(i)*epochs)+'.h5')
    print('ok')
    plt.savefig('Plot_RMS_loss_peaks_'+str(factorial(i)*epochs)+'.png')
    plt.close()
    prediction = model.predict(testing_x)
    for idx in range(100):
        plt.plot(testing_x[idx, :],'k--')
        # plt.plot(prediction[idx,:],'r')
        # plt.plot(testing_y[idx,:],'k--')
        plt.plot(magnet_response(dt, prediction[idx,:]),'r')
        plt.savefig('RMS_loss_peaks_' + str(factorial(i)*epochs) +'_test_'+ str(idx)+'.png')
        plt.close()


# In[ ]:




