# This test requires installing the tensorflow backend: https://www.tensorflow.org/install/
# to do this, type pip install tensorflow in the Anaconda command prompt
# the h5py module http://docs.h5py.org/en/latest/build.html
# and the Keras module
import numpy as np
import matplotlib.pyplot as plt
import time
import tensorflow as tf
#hello = tf.constant('Hello, TensorFlow!')
#sess = tf.Session()
#print(sess.run(hello))

import keras as ks

from testing.Magnet_simulation.virtual_magnet import magnet_response

N_sets = 30000
Set_size = 4000
Max_time = 5

dt = Max_time/Set_size

r1 = np.random.rand(N_sets,) *2*np.pi

training_x = np.empty([N_sets, Set_size,1])  # List of input numpy arrays
# training will consist of one vector:
# time vector from 0 to r1 in 25000 steps
training_y = np.empty([N_sets, Set_size,1])
#  target output will consist of two vectors, one will be a sine wave with amplitude sqrt(r2)/r1

for idx, item in enumerate(r1):
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

    signal = A1*np.sin(2*np.pi*F1*t_vector+F1) + A2*np.sin(2*np.pi*F2*t_vector+F2) + A3*np.sin(2*np.pi*F3*t_vector+F3)+A4*np.sin(2*np.pi*F4*t_vector+F4)

    training_x[idx, :, 0] = (magnet_response(dt, signal)+ 2) / 8
    training_y[idx, :, 0] = (signal + 2) / 8

testing_x = np.empty([300, Set_size,1])  # List of input numpy arrays
testing_y = np.empty([300, Set_size,1])

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

    signal = A1 * np.sin(2 * np.pi * F1 * t_vector + F1) + A2 * np.sin(2 * np.pi * F2 * t_vector + F2) + A3 * np.sin(
        2 * np.pi * F3 * t_vector + F3) + A4 * np.sin(2 * np.pi * F4 * t_vector + F4)

    testing_x[idx, :, 0] = (magnet_response(dt, signal)+ 2) / 8
    testing_y[idx, :, 0] = (signal + 2) / 8

from keras.layers import Input, Dense, Conv1D, GaussianNoise
from keras.models import Model

# This returns a tensor
inputs = Input((Set_size,1))
print(inputs.shape)
print(training_x.shape)
print(training_y.shape)

# a layer instance is callable on a tensor, and returns a tensor
cv = Conv1D(20,1000,padding='same')(inputs)
print(cv.shape)
# n = GaussianNoise(2)(cv)
x = Dense(1, activation='relu')(cv)
#x = Dense(1, activation='relu')(x)
predictions = Dense(1, activation='relu',use_bias=True)(x)

# This creates a model that includes
# the Input layer and three Dense layers
model = Model(inputs=inputs, outputs=predictions)
model.compile(loss='mean_squared_error', optimizer='Adagrad',
              metrics=['accuracy'])

model.fit(training_x, training_y, epochs=35,
          batch_size=64)  # starts training

print('ok')

prediction = model.predict(testing_x)

for idx in range(N_sets):
    plt.plot(prediction[idx,1500:1800],'r')
    plt.plot(testing_y[idx,1500:1800],'g')
    plt.plot(testing_x[idx, 1500:1800],'k')
    plt.show()
    time.sleep(0.5)
    plt.close()
