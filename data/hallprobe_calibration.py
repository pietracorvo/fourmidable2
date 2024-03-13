import h5py
import numpy as np
from sklearn import linear_model
import matplotlib.pyplot as plt
import json

import pandas as pd


def get_rot_matrix(angle):
    angle = np.radians(-angle)
    c, s = np.cos(angle), np.sin(angle)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return R


def get_hallprobe_calibration(filename, plot=False):
    # read the data
    with h5py.File(filename, 'r') as file:
        t = file.get('/hallprobe/data')[:, 0]
        t -= t[0]
        hp = file.get('/hallprobe/data')[:, 1:]
        bighp = file.get('/bighall_fields/data')[:, 1:]
        position = file.get('/stage/data')[:]

    angle = position[3]
    R = get_rot_matrix(angle)
    bighp = bighp.dot(R)

    # do the linear regression on the two sets of data
    regr = linear_model.LinearRegression(
        fit_intercept=False, normalize=False)

    regr.fit(hp, bighp)
    r = regr.score(hp, bighp)
    n = np.shape(bighp)[0]

    result = {
        'coefficients': regr.coef_,
        'intercept': regr.intercept_,
        'score': r
    }
    print('Intercept: \n', result['intercept'])
    print('Coefficients: \n', result['coefficients'])
    print('Score: \n', result['score'])

    result['coefficients'] = result['coefficients'].tolist()
    with open('hallprobe_calib_data.json', 'w') as outfile:
        json.dump(result, outfile)

    # visualise the predicion
    data = np.hstack((t[:, np.newaxis], hp, bighp))
    pred = regr.predict(hp)
    err = bighp - pred
    stdev = np.std(err)
    print('St dev: ', stdev)

    if plot:
        # compare the fields
        plt.figure()
        plt.plot(t, bighp[:, 1], label='big hallprobe')
        plt.plot(t, pred[:, 1], label='small hallprobes')
        plt.xlabel('t [s]')
        plt.ylabel('field [mT]')
        plt.legend()
        plt.title('Comparison of predicted vs real fields')
        plt.grid()

        # show the errors
        plt.figure()
        relative_err = bighp - pred
        plt.plot(t, relative_err[:, 0])
        plt.xlabel('t [s]')
        plt.ylabel('Error [mT]')
        plt.title('Error in the prediction')
        plt.grid()

        # calculate the relative error after binning
        nbins = 100  # number of bins per second

        mn = np.min(t)
        mx = np.max(t)
        bins = np.linspace(mn, mx, np.round(
            (mx - mn) * 1000 / nbins).astype(int))
        data = pd.DataFrame({"t": t, "err": relative_err[:, 0]})
        data['bins'] = pd.cut(data['t'], bins=bins, right=False)
        data = data.groupby('bins').mean().reset_index()
        data.dropna(inplace=True)

        plt.figure()
        plt.plot(data["t"], data["err"])
        plt.xlabel('t [s]')
        plt.ylabel('Error [mT]')
        plt.title(
            'Error in the prediction, filtered (n_bins= {})'.format(nbins))
        plt.grid()

        plt.show(block=True)

    return result, pred, data


if __name__ == "__main__":
    filename = "HallprobeCalib_20201026-1701.h5"
    get_hallprobe_calibration(filename)
