import h5py
import numpy as np
import matplotlib.pyplot as plt


def loop_analysis(file_name):
    with h5py.File(file_name, 'r') as file:
        loops = file.get('/loops').keys()
        # cycle through each of the position groups and get the average data for each of the sequences
        woll = file.get('loops/loop550/wollaston/data')


        # woll_s = woll_list[:, 1]
        # woll_p = woll_list[:, 2]
        # hp = hp_list[:, 1]
        fig = plt.figure()
        a1 = fig.add_subplot(121)
        a2 = fig.add_subplot(122)
        a1.plot(woll[:, 0], woll[:, 1])
        a1.set_xlabel('t [s]')
        a1.set_ylabel('Wollaston signal 1')
        a2.plot(woll[:, 0], woll[:, 2])
        a2.set_xlabel('t [s]')
        a2.set_ylabel('Wollaston signal 2')
        plt.tight_layout()
        fig2 = plt.figure()
        a2 = fig2.add_subplot(121)
        a3 = fig2.add_subplot(122)
        a2.plot(woll[:, 0], (woll[:, 1]-woll[:, 2])/( woll[:, 2]+woll[:, 1]))
        a2.set_xlabel('t [s]')
        a2.set_ylabel('Average')
        a3.plot(woll[:, 0], woll[:, 2]+woll[:, 1])
        a3.set_xlabel('t [s]')
        a3.set_ylabel('Difference')
        plt.show()



if __name__ == '__main__':
    loop_analysis(r'../gui/acquired_data/LoopTaking_20181018-141047 laser moved away from kepkos.h5')