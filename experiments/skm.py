import numpy as np
import h5py
import pandas as pd
import sys
from data.signal_generation import stack_funs, get_zeros_signal
# CODE MODIFIED
#import smaract.ctl as ctl
import traceback
import time
import csv


def GetSerpentineSignal(moke, pt0, delta, hor, ver):
    # Function used to create serpentine-like points to raster through in SKM
    #First, we generate a serpentine just on the XY plane.
    x0 = pt0[0]  # Coordinates x and z may be swapped around, x-2 and z-0
    y0 = pt0[2]
    z0 = pt0[1]

    nw_0 = np.asarray([pt0[0], pt0[1], pt0[2]])

    angle_r = np.radians(pt0[3])

    R_z = [[np.cos(angle_r), -np.sin(angle_r), 0.0], [np.sin(angle_r), np.cos(angle_r), 0.0], [0.0, 0.0, 1.0]]

    #new_0 = np.dot(R_inv_z, nw_0)

    x_vector = np.arange(0, hor) * delta
    y_vector = np.arange(0, ver) * delta

    X, Y = np.meshgrid(x_vector, y_vector)
    X[1::2, :] = np.flip(X[1::2, :])

    X_flat = X.flatten() - (0.5 * hor * delta)
    Y_flat = Y.flatten() - (0.5 * ver * delta)

    size = len(X_flat)
    i=0
    position=list()

    #Now we get the current angle from the Smaract
    smaract = moke.instruments['stage']
    #initial_pos = smaract.get_position()
    X_rot = list()
    Y_rot = list()
    Z_rot = list()

    #We use Luka' s function to rotate into the F.O.R. of the sample (the same used everywhere else in MokePy)
    for i in range(size):
        unrotated = np.asarray([X_flat[i], 0.0, Y_flat[i]])
        rotated = np.dot(R_z, unrotated)
        rotated = unrotated.astype(int)
        X_rot.append(rotated[0]+ nw_0[0])
        Y_rot.append(rotated[2] + nw_0[1])
        Z_rot.append(rotated[1]+ nw_0[2])

    #Vector data in Smaract form (C:/SmarAct/MCS2/Documentation/MCS2ProgrammersGuide.pdf pag. 71)
        vector = np.asarray([0, rotated[0], 1, rotated[1], 2, rotated[2]])
    return X_rot, Y_rot, Z_rot


def skm_map_smaract(moke, delta, delta_z, hor, ver, sag, rate, int_time, acceler):
    # pt0: initial starting point (in um due to calibration)
    # delta: spacing between points (um)
    # npoints: number of points along a single direction (total points npoints*npoints)
    # velocity: velocity at which we operate system (pm/s)
    try:

        #if source == 1:
        wollaston1 = moke.instruments['wollaston1']
        #else:
        wollaston2 = moke.instruments['wollaston2']

        # Get Smaract Stage
        smaract = moke.instruments['stage']
        initial_pos = smaract.get_position()

        # Get the points we want to measure at
        x_coord, y_coord, z_coord = GetSerpentineSignal(moke, initial_pos, delta=delta, hor=hor, ver=ver)

        #data = np.genfromtxt('C:/Users/3Dstation3/Desktop/StreamSerpentine.txt', dtype=np.int64)
        position = list(list())
        size = len(x_coord)
        idx_tot = 0

        #Global chronometer
        init_time = time.time()

        # Set stream speed in Hz and start the stream
        #smaract.openStream(rate)
        speed = [1000000*rate, 1000000*rate, 1000000*rate]
        smaract.set_velocity(speed)

        #Default acceleration value is 100 * 10^9 pm/s^2
        #acceler = 100000000000
        acceleration = [acceler, acceler, acceler, 0]
        smaract.set_acceleration(acceleration)

        sag = int(sag) + 1
        print('SAG', sag)

        woll_1 = np.zeros((sag, size))
        woll_2 = np.zeros((sag, size))
        woll_3 = np.zeros((sag, size))
        woll_4 = np.zeros((sag, size))

        for sagittal in range(sag):
            for idx in range(size):

                z_coord[idx] += sagittal * delta_z

                #Stream mode
                #vector = np.asarray([0, x_coord[idx], 1, y_coord[idx], 2, z_coord[idx]])
                #smaract.streamFrame(vector)

                #Single point mode
                vectorPos = np.asarray([x_coord[idx], y_coord[idx], z_coord[idx]])
                smaract.set_position(vectorPos / 1.0, False, True)

                position.append(smaract.get_position())

                st = wollaston1.get_time()
                WWD_arm1 = wollaston1.get_data(start_time=st, end_time=st + int_time)
                WWD_arm2 = wollaston2.get_data(start_time=st, end_time=st + int_time)
                WD1 = WWD_arm1['det1'].mean()
                WD2 = WWD_arm1['det2'].mean()
                WD3 = WWD_arm2['det1'].mean()
                WD4 = WWD_arm2['det2'].mean()

                woll_1[sagittal, idx] = WD1
                woll_2[sagittal, idx] = WD2
                woll_3[sagittal, idx] = WD3
                woll_4[sagittal, idx] = WD4

                idx_tot += 1
                print('%.4f' % WD1, ':', '%.4f' % WD2, ':', '%.4f' % WD3, ':', '%.4f' % WD4, '   ', '%.2f' % (100.0 * idx_tot / (size * sag)), '%')

        #Go back to the initial position
        smaract.set_position(initial_pos, False, True)

        np.savetxt('C:/Users/3Dstation3/Desktop/WollData_1.txt', woll_1, fmt='%.8f')
        np.savetxt('C:/Users/3Dstation3/Desktop/WollData_2.txt', woll_2, fmt='%.8f')
        position = np.asarray(position)
        np.savetxt('C:/Users/3Dstation3/Desktop/PosData.txt', position, fmt='%.8f')

        #smaract.closeStream()
        #Back to the default closed-loop acceleration
        #smaract.set_acceleration([0, 0, 0, 0])

        final_time = time.time()
        tot_time = (final_time - init_time) * 1000

        print('Execution time (ms) = ', '%.3f' % (tot_time/60000.0), 'minutes')
        print('Experiment finished')

    except:
        traceback.print_exc()
    return position, woll_1, woll_2, woll_3, woll_4


def process_skm(pos_data, WD_1, WD_2, hor, ver, mix):
    print('Processing: ', mix)

    WD_1 = np.asarray(WD_1)
    WD_2 = np.asarray(WD_2)

    if mix == 'Sum':
        data_mix = WD_1 + WD_2
    if mix == 'Diff':
        data_mix = WD_1 - WD_2
    if mix == 'Det 1':
        data_mix = WD_1
    if mix == 'Det 2':
        data_mix = WD_2
    if mix == 'Avg':
        data_mix = (WD_1 + WD_2) * 0.5

    wdd = {'det1': data_mix}
    wollaston_data = pd.DataFrame(wdd)
    wollaston_data.to_csv('C:/Users/3Dstation3/Desktop/WollDataTOT.txt', index=False, header=False)

    # create the image out of tuples and wollaston data
    image = np.zeros((hor, ver))
    c = np.array(data_mix)
    sweep = np.asarray(range(0, hor, 1))

    for Y in range(0, ver):
        ind = 0
        sweep2 = sweep + hor * Y
        if (((Y + 1) % 2) == 0):
            sweep2 = np.flip(sweep2)
        for X in sweep2:
            image[ind, Y] = c[X]
            ind += 1

    #image = np.flip(image, axis=0)
    # normalise the image
    #image -= np.min(image)
    #image /= np.max(image)
    return image


if __name__ == "__main__":
    from control.instruments.moke import Moke
    import time

    with Moke() as moke:
        time.sleep(0.5)
        pos, woll_1, woll_2 = skm_map_smaract(moke, 1.0, 100, 500)
