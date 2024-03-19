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

N_sets = 30000
Set_size = 4000
Max_time = 100
Renorm = 3
r1 = np.random.rand(N_sets,) * 5
r2 = np.random.rand(N_sets,)
r3 = np.random.rand(N_sets,) * 8 + 1
training_x = np.empty([N_sets, Set_size,1])  # List of input numpy arrays
# training will consist of one vector:
# time vector from 0 to r1 in 25000 steps
training_y = np.empty([N_sets, Set_size,1])
#  target output will consist of two vectors, one will be a sine wave with amplitude sqrt(r2)/r1

for idx, item in enumerate(r1):
    training_y[idx, :,0] = np.sin((np.linspace(0, Max_time, Set_size)+item)*r3[idx])*r2[idx]/Renorm + 1.2*r2[idx]/Renorm
    training_x[idx, :,0] = np.sin((np.linspace(0, Max_time, Set_size)+item)*r3[idx]+r3[idx])*r2[idx]/Renorm/2 + 0.7*r2[idx]/Renorm

r1 = np.random.rand(N_sets,) * 5
r2 = np.random.rand(N_sets,)
r3 = np.random.rand(N_sets,) * 8 + 1
testing_x = np.empty([N_sets, Set_size,1])  # List of input numpy arrays
# training will consist of one vector:
# time vector from 0 to r1 in 25000 steps
testing_y = np.empty([N_sets, Set_size,1])
#  target output will consist of two vectors, one will be a sine wave with amplitude sqrt(r2)/r1

for idx, item in enumerate(r1):
    testing_y[idx, :,0] = np.sin((np.linspace(0, Max_time, Set_size)+item)*r3[idx])*r2[idx]/Renorm + 1.2*r2[idx]/Renorm
    testing_x[idx, :,0] = np.sin((np.linspace(0, Max_time, Set_size)+item)*r3[idx]+r3[idx])*r2[idx]/Renorm/2 + 0.7*r2[idx]/Renorm

from keras.layers import Input, Dense, Conv1D
from keras.models import Model

# This returns a tensor
inputs = Input((Set_size,1))
print(inputs.shape)
print(training_x.shape)
print(training_y.shape)

# a layer instance is callable on a tensor, and returns a tensor
cv = Conv1D(50,700,padding='same')(inputs)
print(cv.shape)
x = Dense(Set_size, activation='relu')(cv)
#x = Dense(Set_size, activation='relu')(x)
predictions = Dense(1, activation='relu')(x)

# This creates a model that includes
# the Input layer and three Dense layers
model = Model(inputs=inputs, outputs=predictions)
model.compile(loss='mean_squared_error', optimizer='sgd',
              metrics=['accuracy'])

model.fit(training_x, training_y, epochs=5,
          batch_size=64)  # starts training

print('ok')

prediction = model.predict(testing_x)
for idx in range(N_sets):
    plt.plot(prediction[idx,1:],'r')
    plt.plot(testing_y[idx,1:],'g')
    plt.plot(testing_x[idx, 1:],'k')
    plt.show()
    time.sleep(0.5)
    plt.close()
