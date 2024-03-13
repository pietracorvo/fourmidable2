import numpy as np
import pickle
import time
import h5py
import data.signal_generation as signals
import control.exceptions as myexceptions
from warnings import warn
from data.signal_processing import filter_signal_pd as filter_data
import pandas as pd


def zero_magnet(moke):
    """Puts a zero signal on all poles of the magnet"""
    moke.instruments["hexapole"].stage_data(
        signals.get_zeros_signal(), 1, autostart=True, use_calibration=False)


def set_baseline(moke):
    """Starts a baseline output to each of the dipoles

    Args:
        moke: handle to moke object
        period: period of sin wave signal. Can be a number (if same for all dipoles) or a list
        amplitudes: amplitude of the signal
    """
    # set the temperature reference signal
    moke.instruments["reference"].stage_data(
        lambda x: np.zeros(len(x)), 1, autostart=True)
    # set the magnets to 0
    zero_magnet(moke)


def deGauss(moke):
    """Starts a baseline output and deGausses the magnets, leaving them at 0

    Args:
        moke: handle to moke object
        period: period of sin wave signal. Can be a number (if same for all dipoles) or a list
        amplitudes: amplitude of the signal
    """
    magnet = moke.instruments['hexapole']
    # set the baseline
    set_baseline(moke)
    time.sleep(0.1)

    # degauss and zeros after
    degauss_time = 3
    zeros_time = 1
    degauss_fun, dz_time = signals.stack_funs([
        signals.get_deGaussing_fun(),
        lambda x: np.zeros(len(x))
    ],
        [degauss_time, zeros_time])
    magnet.stage_data([degauss_fun] * 3, [dz_time] * 3,
                      autostart=True, use_calibration=False)
    t0 = magnet.get_time()
    print('waiting for degauss')
    magnet.wait_for_time(t0 + degauss_time + 0.5)
    zero_magnet(moke)
    print('degauss finished')


def temp_too_high(moke, max_temp=50, print_values=True):
    """Checks the temperature of moke and returns true or false depending on is it bigger or lower than max_temp"""
    temp = moke.instruments['temperature']
    temp_data = temp.get_data(start_time=-5)
    # average over the data
    temp_mean = temp_data.mean()
    if print_values:
        # print the current temperature
        print('Current temperature: \n', temp_mean)
    if (temp_mean > max_temp).any():
        print('Coils too hot!')
        return True
    return False


def temp_too_high_stop(moke, max_temp=50, stop_event=None):
    """Checks if the temperature is too hot (given by max_temp) and if so sets all magnet outputs to 0 and waits for the temperature to go below 35. 
    If there is no hexapole instrument, this function fails! If stop event is set, the function returns even if the magnets are too hot.

    Args:
        moke: Moke object containing hexapole instrument
        max_temp (num): stopping temperature
        stop_event (threading.Event): event which if set lets the function return even if the temperature is too high
    """

    # check if the temperature is too hot. If so, immediately put the current to 0 and wait
    magnet = moke.instruments['hexapole']
    zeros_signal = [
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x))
    ]
    if temp_too_high(moke, max_temp):
        magnet.stage_data(zeros_signal, 1)
        # wait until at least as low as 35
        while temp_too_high(moke, 35):
            if (stop_event is not None) and (stop_event.is_set()):
                break
            print(
                'Temperature too high, will wait until it goes below ', 35)
            time.sleep(5)
            continue


def wait_for_time_check_temp(moke, end_time, stop_event=None):
    """ Function waits for time and if too high of a temperature is reached, 
    the experiment is aborted"""

    # check if the temperature is too hot. If so, immediately put the current to 0 and wait
    magnet = moke.instruments['hexapole']
    zeros_signal = [
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x))
    ]
    t0 = magnet.get_time()
    t_check = t0
    while t0 <= end_time:
        # check temperature every 2 seconds
        if t0 > t_check + 2:
            t_check = t0
            if temp_too_high(moke):
                print('Temperature too high! Aborting')
                magnet.stage_data(zeros_signal, 1)
        # check if the stop event was triggered
        if (stop_event is not None) and (stop_event.is_set()):
            magnet.stage_data(zeros_signal, 1)
            break
        # keep going
        t0 = magnet.get_time()
        time.sleep(0.1)


def switch_laser(moke, state):
    """Switches the laser on (state=True) or off(state=False)"""
    try:
        laser = moke.instruments['laser']
    except KeyError:
        print('Laser not defined in instruments!!')
        return
    low_voltage, high_voltage = 0, 3
    if state:
        print('Turning laser on')
        laser.stage_data(
            lambda x: high_voltage * np.ones(len(x)), 1, autostart=True)
    else:
        print('Turning laser off')
        laser.stage_data(
            lambda x: low_voltage * np.ones(len(x)), 1, autostart=True)


def magnet_loop_tuning(moke, signal, period, tune_start, stop_event, parameters=None):
    """
    The experiment tunes the magnet output loop based on the desired output functions and the hallprobe feedback.
    For this to work, either the moke instrument has to have the PID loop tuning parameters in its settings, 
    or we have to pass the PID parameters in the form of a dictionary
    """
    if parameters is None:
        # for this to work, loop tuning parameters have to be defined in the settings
        assert "loop_tuning" in moke.settings_data
        parameters = moke.settings_data["loop_tuning"]
    Kp = parameters["Kp"] if "Kp" in parameters else 0
    Ki = parameters["Ki"] if "Ki" in parameters else 0
    Kd = parameters["Kd"] if "Kd" in parameters else 0
    # assert not all([Kp == 0, Ki == 0, Kd == 0])

    magnet = moke.instruments['hexapole']
    hp = moke.instruments['hallprobe']

    # define some helper parameters
    rate = magnet.controller.rate
    n_data = int(rate * period)
    integral = np.zeros((n_data, 3))
    previous_error = np.zeros((n_data, 3))
    # define the wanted signal values
    t = np.linspace(0, period, n_data)
    values = np.vstack([f(t) for f in signal]).T
    signal_wanted = pd.DataFrame(values,
                                 columns=hp.ports.values(), index=t)

    # start tuning the loop
    while True:
        magnet.wait_for_time(tune_start + period, stop_event)
        if stop_event.is_set():
            break
        # get the wanted and measured data from the last period
        signal_measured = hp.get_data(start_time=tune_start,
                                      end_time=tune_start + period)
        output_data = magnet.get_data(start_time=tune_start,
                                      end_time=tune_start + period).values
        # so far found that filtering doesn't work well because it can introduce edge effects
        # signal_measured = filter_data(hp_data)
        # output_data = filter_data(magnet.get_data(start_time=tune_start,
        #                                           end_time=tune_start + period)).values
        # sometimes the acquired signals have one more/less tick
        diff = signal_measured.shape[0] - n_data
        # print('Differences:')
        # print(diff)
        # print(n_data)
        # print(signal_measured.shape[0])
        # print(output_data.shape[0])
        if diff < 0:
            values = signal_measured.values
            # repeat the last few points
            values = np.vstack(
                [values, values[diff:, :]])
            signal_measured = pd.DataFrame(values,
                                           columns=signal_measured.columns,
                                           index=t)
        elif diff > 0:
            signal_measured = signal_measured.iloc[:n_data, :]
        diff = output_data.shape[0] - n_data
        if diff < 0:
            output_data = np.vstack(
                [output_data, output_data[diff:, :]])
        elif diff > 0:
            output_data = output_data[:n_data, :]

        signal_measured.index = t
        # calculate the error and remove the calibration
        error = hp.calibration.data2inst(
            signal_measured - signal_wanted).values
        # print('Max tuning error: ', 27.26 * np.max(error), ' mT')

        # stop correcting if the signal is good enough, wait for longer before checking again
        if np.max(np.abs(error)) < 0.2 / 27.26:
            tune_start += 4 * period
            continue

        # get the output signal
        correction = np.zeros(error.shape)
        if Kp != 0:
            correction += Kp * error
        if Ki != 0:
            integral += error
            correction += Ki * integral
        if Kd != 0:
            derivative = error - previous_error
            correction += Kd * derivative
        output_data += correction

       # print('ERROR======= ', error)
       # print('OUTPUT======= ', output_data)

        # # saving for debugging
        # to_save = {
        #     'correction': correction,
        #     'diff': diff,
        #     'signal_measured': signal_measured_forsave,
        #     'signal_wanted': signal_wanted,
        #     'output_data': output_data
        # }
        # with open('debug.p', 'wb') as f:
        #     print('saved')
        #     pickle.dump(to_save, f)
        # stage the new signal
        magnet.stage_interp(
            t, output_data, use_calibration=False, index_reset=False)
        tune_start += 2 * period

        # make sure that the tuning is not lagging behind the acquisition.
        # if this ever becomes a problem, this can be solved by taking a bigger period and
        # having multiple signal repetitions inside it
        if magnet.get_time() >= tune_start + period:
            warn('Warning! Tuning not keeping up with the data acquisition')
