import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator


from mpl_toolkits.mplot3d import Axes3D
import vtk
import mayavi
from mayavi import mlab
from tvtk.api import tvtk, write_data



from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl

def extract_summary(data_file_name, save_file_name):
    with h5py.File(data_file_name) as file:
        # get the position groups
        position_groups = list([f for f in file.keys() if f not in {
            'position6579', 'position6580'}])

        print(len(position_groups), ' positions measured')

        # iterate through the positions and store the position and average of all three fields for each of the sequences
        col_tuples = [('position', 'x'), ('position', 'y'), ('position', 'z'),
                      ('hallprobe', 'A'), ('hallprobe', 'B'), ('hallprobe', 'C'),
                      ('big_hallprobe', 'x'), ('big_hallprobe',
                                               'y'), ('big_hallprobe', 'z')
                      ]
        data = pd.DataFrame(np.zeros((len(position_groups), len(col_tuples))),
                            columns=pd.MultiIndex.from_tuples(col_tuples))

        with pd.HDFStore(save_file_name, mode='w') as store:
            for j in range(3):
                for i, p in enumerate(position_groups):
                    # get the position
                    print('Position ', i, '/', len(position_groups))
                    data.loc[i, 'position'] = file[p +
                                                   '/LinearStage/data/table'].value.view(np.float64)[1:]
                    # get the sequence data
                    data.loc[i, 'hallprobe'] = pd.DataFrame(
                        file[p + '/Field sequence' + str(j) + '/hallprobe/data/table'].value).mean().values[1:]
                    data.loc[i, 'big_hallprobe'] = pd.DataFrame(
                        file[p + '/Field sequence' + str(j) + '/bighall_fields/data/table'].value).mean().values[1:]
                store.append('/field_sequence' + str(j), data)


def plot_summary(file_name, sequence):
    # get the data
    with pd.HDFStore(file_name) as store:
        data = store.get('field_sequence' + str(sequence))

    # get the set of positions
    x = np.round(np.array(data.loc[:, ('position', 'x')]), decimals=-1).astype(int)
    y = np.round(np.array(data.loc[:, ('position', 'y')]), decimals=-1).astype(int)
    z = np.round(np.array(data.loc[:, ('position', 'z')]), decimals=-1).astype(int)

    fields = np.array(data['big_hallprobe'])
    # npdata = np.vstack((x, y, z, fields[:, 0], fields[:, 1], fields[:, 2]))
    # np.save('test.npy', npdata)
    # initial_data = mlab.pipeline.vector_field(x, y, z, fields[:, 0], fields[:, 1], fields[:, 2])
    # # norm = mlab.pipeline.extract_vector_norm(initial_data)
    # disp = mlab.pipeline.vector_field(initial_data)
    # mlab.show()
    # return

    # create a grid out of the given points:
    x_unique = np.unique(x)
    y_unique = np.unique(y)
    z_unique = np.unique(z)
    x_mesh, y_mesh, z_mesh = np.meshgrid(x_unique, y_unique, z_unique[:-1])
    # get the field norms in the same shape
    # get the norms
    field_norms = np.linalg.norm(np.array(data['big_hallprobe']), axis=1)
    field_mesh = np.empty(x_mesh.shape)
    for i, v in enumerate(field_norms):
        indx = np.argmax(np.sum(np.vstack((x_mesh.flatten(), y_mesh.flatten(), z_mesh.flatten())) == np.array([x[i], y[i], z[i]])[:, None], axis=0))
        field_mesh.flatten()[indx] = v
    full_arr = np.vstack((x_mesh.flatten(), y_mesh.flatten(), z_mesh.flatten(), field_mesh.flatten()))
    with pd.HDFStore('full_arr.h5', 'w') as store:
        store.append('/data',  pd.DataFrame(full_arr.transpose(), columns=[1, 2, 3, 4]))
        store.append('/data2', pd.DataFrame(np.vstack((x.flatten(), y.flatten(), z.flatten(), field_norms.flatten())).transpose(), columns=[1, 2, 3, 4]))
    return
    # print(field_mesh.flatten() == 0)
    # print(field_mesh)
    # mlab.pipeline.vector_field(fields[:, 0], fields[:, 1], fields[:, 2])
    # mlab.volume_slice(field_mesh, plane_orientation='z_axes')
    # mlab.flow(x_mesh,y_mesh,z_mesh,field_mesh)

    # mlab.pipeline.volume(mlab.pipeline.scalar_field(field_mesh))
    # mlab.pipeline.image_plane_widget(mlab.pipeline.scalar_field(field_mesh),
    #                                  plane_orientation='x_axes',
    #                                  slice_index=10,
    #                                  )
    # mlab.show()
    int_f = RegularGridInterpolator((x_unique, y_unique, z_unique[:-1]), field_mesh)

    fig = plt.figure()
    indx = z==-1200
    print(np.array(data['position'].loc[z==-1200]))
    print(int_f(np.array(data['position'].loc[z==-900]-2)))
    print(x[indx].shape)
    plt.tricontourf(x[indx], y[indx],int_f() , 10, cmap="jet")
    cbar = plt.colorbar()
    plt.show()

    # ax = fig.add_subplot(111, projection='3d')
    #
    # ax.quiver(x, y, z, fields[:, 0], fields[:, 1], fields[:, 2])
    # plt.show()



def field_map_processing(file_name, sequence):
    with pd.HDFStore(file_name) as store:
        # get the position groups
        position_groups = sorted({p.split('/')[1] for p in list(store.keys())})
        # cycle through each of the position groups and get the average data for each of the sequences
        positions = pd.concat(
            [store.get('/' + p + '/LinearStage/data') for p in position_groups])
        bighp = []
        hp = []
        for p in position_groups:
            print(p)
            # get the field sequence means
            hp_norm = []
            bighp_norm = []
            for i in range(3):
                hp_raw_data = store.get(
                    '/' + p + '/Field sequence' + str(i) + '/hallprobe/data')
                bighp_raw_data = store.get(
                    '/' + p + '/Field sequence' + str(i) + '/bighall_fields/data')
                # get the norm of the means
                hp_norm.append(np.linalg.norm(hp_raw_data.mean()))
                bighp_norm.append(np.linalg.norm(bighp_raw_data.mean()))
            hp.append(hp_norm)
            bighp.append(bighp_norm)
        bighp = np.array(bighp)
        hp = np.array(hp)
    # xy = np.delete(positions[positions[:, 2] == 0], 2, axis=1)
    xy = positions.loc[:, ['x', 'y']]
    z = bighp[:, sequence]

    ax = plt.subplot(1, 3, sequence + 1)
    plt.tricontourf(xy['x'], xy['y'], z, 10, cmap="jet")
    cbar = plt.colorbar()
    # plt.scatter(xy[:, 0], xy[:, 1], c=z, cmap="jet")
    ax.set_title('sequence ' + str(sequence))
    ax.set_xlabel('x [um]')
    ax.set_ylabel('y [um]')
    cbar.set_label('B [mT]')

    # plt.axis('equal')
    # plt.axis([xy['x'].min(), xy['x'].max(), xy['y'].min(), xy['y'].max()])


if __name__ == '__main__':
    # extract_summary(r'C:\Users\user\Documents\Python\MOKEpy\gui\field_map20181112-1405.h5',
    #                 r'C:\Users\user\Documents\Python\MOKEpy\gui\field_map20181112-1405_summary.h5')

    plot_summary(
        r'D:\University Of Cambridge\Amalio Fernandez-Pacheco - Dark Field MOKE\field_map20181112-1405_summary.h5', 0)

    # plt.figure(figsize=(15, 4))
    # for i in range(3):
    #     field_map_processing(
    #         r'C:\Users\user\Documents\Python\MOKEpy\gui\field_map20181109-1710.h5', i)
    #     # plt.savefig('sequence'+str(i))
    #
    # plt.tight_layout(pad=0.3, w_pad=1, h_pad=1)
    # plt.show()
