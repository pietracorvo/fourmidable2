import numpy as np
# import pandas as pd
import matplotlib.pyplot as plt
from .data_analysis import get_fields_dir_vector


def plot_fields(data, ax=None):
    if ax is None:
        fig, ax = plt.subplots()
    ax.plot(data['t'], data['Bx'], label='X', linewidth=3)
    ax.plot(data['t'], data['By'], label='Y', linewidth=3)
    ax.plot(data['t'], data['Bz'], label='Z', linewidth=3)
    ax.legend()
    ax.set_xlabel('t [s]')
    ax.set_ylabel('B [mT]')


def plot_moke(data, ax=None, direction='fields', detector='both'):
    """Plots the moke signal for both detectors along the given direction"""
    if ax is None:
        fig, ax = plt.subplots()
    fields = data.loc[:, ['Bx', 'By', 'Bz']]
    if isinstance(direction, np.ndarray):
        dir_vector = direction / np.linalg.norm(direction)
        fields_label = 'B'
    else:
        if direction == 'fields':
            dir_vector = get_fields_dir_vector(data)
            fields_label = 'Babs'
        elif direction == 'x':
            dir_vector = np.array([1, 0, 0])
            fields_label = 'Bx'
        elif direction == 'y':
            dir_vector = np.array([0, 1, 0])
            fields_label = 'By'
        elif direction == 'z':
            dir_vector = np.array([0, 0, 1])
            fields_label = 'Bz'
        else:
            raise Exception('Unrecognised direction')

    fields_dir = fields.dot(dir_vector)

    if detector == 'both':
        ax.plot(fields_dir, data['moke1'], label='Structure', alpha=0.9)
        ax.plot(fields_dir, data['moke2'], label='Substrate', alpha=0.9)
    else:
        ax.plot(fields_dir, data['moke' + str(detector)], label='Structure')

    ax.legend()
    ax.set_xlabel(fields_label + ' [mT]')
    ax.set_ylabel('Kerr effect')


def plot_derivatives(data, peaks):
    fig, ax = plt.subplots(2, 2, figsize=[14, 8])
    t = data['t']
    for i, key in enumerate(['moke1', 'moke2']):
        deriv = data[key + '_deriv']
        ax[0, i].plot(t, data[key])
        ax[1, i].scatter(t[peaks[key]], deriv[peaks[key]],
                         marker="x", s=100, color='red')
        ax[1, i].plot(t, deriv)
        # ax[1, i].set_ylim([-0.05, 0.05])
        # ax[0, i].set_ylim([-5.5e-4, 5.5e-4])
        ax[1, i].set_xlabel('t [s]')
    ax[0, 0].set_ylabel('Kerr signal')
    ax[1, 0].set_ylabel('Kerr signal derivative')
    ax[0, 0].set_title('Structure')
    ax[0, 1].set_title('Substrate')
    return fig, ax
