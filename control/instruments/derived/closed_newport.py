from control.instruments.basic import Instrument, np
from control import load_from_settings as load
import threading
import time
import copy
import warnings
import pandas as pd
import traceback
from termcolor import colored


class ClosedNewport(Instrument):
    """Class defining motors of the Newport controller together with the added angle measurement

        The class inherits Newport class.
    """

    def __init__(self, *, controller, subinstruments, **kwargs):
        """Sets the default properties.

        Args:
            controller: Newport controller class defined in the controllers
            motors: str or list of str containing the number of motor in question. E.g. '1' for motor 1 or ['1', '2']
            for motors '1' and '2'
            kwargs: keyword arguments of the Instrument class
        """
        Instrument.__init__(self, controller=controller, **kwargs)

        self.instruments = load.load_instruments(
            self, subinstruments, controller)

        assert len(self.instruments['angle_measurement'].ports) == 2 * len(
            self.instruments['newport'].motors), """Wrong number of motors or ports in the measurement instrument"""

        # define the thread which sets the position
        self.set_position_thread = threading.Thread(
            target=self.set_position_worker)
        self.set_position_thread.daemon = True
        self.movement_stop = threading.Event()

        # lock which doesn't let multiple commands be sent at the same time
        self.newport_lock = threading.Lock()

        self.update_position_thread = threading.Thread(
            target=self.update_position_worker)
        self.current_position_lock = threading.Lock()
        self.update_position_thread.daemon = True
        self.update_position_stop = threading.Event()
        # define the time when the position was last updated and its lock
        self.last_update_t = 0
        self.last_update_t_lock = threading.Lock()

        # define the variable current position which is going to be constantly updated
        self.current_position = self.get_position(ignore_np=False)
        # define the target position. Useful for live updating
        self.target_position = self.current_position
        # max step size: maximum amount of movement in any particular direction it is going to do at once
        self.max_step_size = 200
        # start updating the position
        self.update_position_thread.start()

    def update_position_worker(self):
        """Continuously updates the position of the motor"""
        sleep_t = 0.1
        # before we start, get all the data and calculate how much we moved
        try:
            while not self.update_position_stop.is_set():
                time.sleep(sleep_t)
                # get the data from the angle measurement
                self.last_update_t_lock.acquire(True)
                data = self.instruments['angle_measurement'].get_data(start_time=self.last_update_t)
                self.last_update_t_lock.release()
                if data.shape[0] == 0:
                    # print('no closed newport data')
                    continue
                # print('Acquired times: ', data.index[0], data.index[-1])
                chA = np.array(data[data.columns[::2]]).astype(float)
                chB = np.array(data[data.columns[1::2]]).astype(float)
                ds = self.delta_steps(chA, chB)
                delta_steps = np.sum(ds, axis=0)
                delta_position = self.calibration.inst2data(delta_steps)
                # update the current position
                self.last_update_t_lock.acquire(True)
                self.current_position_lock.acquire(True)
                self.current_position = np.array(self.current_position) + delta_position

                self.current_position_lock.release()

                self.last_update_t = data.index[-1]
                self.last_update_t_lock.release()
        except:
            traceback.print_exc()
        warnings.warn('Stopping updating the newport position!')

    @staticmethod
    def delta_steps(chA, chB):
        """Calculates deltas based on the channel measurements

            Args:
                chA: measurements of the channel A
                chB: measurements of the channel B

            Returns:
                steps: an array of length 
        """
        # get the changes in the channels
        chA_delta = chA[:-1, :] - chA[1:, :]
        chB_delta = chB[:-1, :] - chB[1:, :]
        # get the state of the channel for each of the switches
        sign_A = np.sign(chA[:-1, :] - 0.5)
        sign_B = np.sign(chB[:-1, :] - 0.5)
        # calculate the number of steps
        steps = chA_delta * sign_B - chB_delta * sign_A
        return steps

    def set_position_worker(self, position):
        resolution = 4 * np.abs(np.array(self.calibration.parameters))
        while True:
            # get the starting position
            start_position = self.get_position()
            # let the motor know where it is right now
            self.define_current_position(start_position, wait=True)
            # calculate the move position so as not to exceed max step size
            delta_wanted = np.array(position) - np.array(start_position)
            for i, d in enumerate(delta_wanted):
                if np.abs(d) > self.max_step_size:
                    delta_wanted[i] = self.max_step_size * np.sign(d)
            move_position = list(np.array(start_position) + np.array(delta_wanted))

            # set the motors moving to the given position
            self.newport_lock.acquire(True)
            self.instruments['newport'].set_position(move_position, wait=False)
            self.newport_lock.release()

            # wait until the position is reached
            self.newport_lock.acquire(True)
            is_moving = self.instruments['newport'].is_moving()
            self.newport_lock.release()
            while is_moving and not self.movement_stop.is_set():
                self.newport_lock.acquire(True)
                is_moving = self.instruments['newport'].is_moving()
                self.newport_lock.release()
                time.sleep(0.05)
            if self.movement_stop.is_set():
                break

            # once the position is reached, get the current position and restart the loop
            current_position = self.get_position()
            if all(np.abs(np.array(current_position) - np.array(position)) < resolution):
                break
            else:
                # check that we are moving in the right direction
                delta_made = np.array(current_position) - np.array(start_position)
                # if the difference is smaller than the resolution, ignore
                factor_off = np.array([w / m if m != 0 and np.abs(
                    w - m) > r else 1 for w, m, r in zip(delta_wanted, delta_made, resolution)])
                # if any of the factors are off, warn the user (meaning that direction movements are getting coupled or
                # the calibration is wrong). However, keep moving in case this is just a minor error
                if any(factor_off <= 0):
                    print('Movement in a wrong direction detected!')
                    print('delta_wanted', copy.deepcopy(delta_wanted))
                    print('delta_made', copy.deepcopy(delta_made))

                # check that we are moving (made at least 10% of the motion)
                for i, f in enumerate(factor_off):
                    if f > 10:
                        print(colored('Motor ' + list(self.instruments['newport'].motors.values())[i] + ' not moving enough!', 'red'))
                        print('delta_wanted', copy.deepcopy(delta_wanted))
                        print('delta_made', copy.deepcopy(delta_made))

    def set_position(self, position, relative=False, wait=True):
        """Moves the motor to the given position after calibration"""
        if self.set_position_thread.is_alive():
            self.set_position_thread.join()
        self.movement_stop.clear()
        if relative:
            position = [p + q for p, q in zip(position, self.get_position())]
        self.target_position = position
        self.set_position_thread = threading.Thread(
            target=self.set_position_worker, args=(position,))
        self.set_position_thread.daemon = True
        self.set_position_thread.start()
        if wait:
            self.set_position_thread.join()

    def set_velocity(self, vel):
        """Sets the velocity of the motors"""
        self.newport_lock.acquire(True)
        self.instruments['newport'].set_velocity(vel)
        self.newport_lock.release()

    def get_position(self, historical=False, start_time=0, end_time=-1, wait=True, ignore_np=True):
        """Gets the current position of the motor after calibration"""
        assert not historical or (start_time != 0 or end_time != -
        1), "start_time and end_time should only be used if historical=True"
        # check if the current position thread is running and if so, get the data from there
        if not self.update_position_thread.is_alive() and not ignore_np:
            if historical:
                raise RuntimeError('The position thread is not running, can not get historical data')
            self.newport_lock.acquire(True)
            position = self.instruments['newport'].get_position()
            self.newport_lock.release()
            return position
        if not self.update_position_thread.is_alive() and ignore_np:
            raise RuntimeError('The position thread is not running!')
        self.current_position_lock.acquire(True)
        last_position = copy.deepcopy(self.current_position)
        last_update_t = copy.deepcopy(self.last_update_t)
        self.current_position_lock.release()
        if not historical:
            return list(last_position)
        # if we went through this block, historical is True
        if last_update_t < end_time:
            raise ValueError('End time has not been reached yet')
        data = self.instruments['angle_measurement'].get_data(start_time=start_time, end_time=end_time, wait=wait)

        # get where the steps happen:
        chA = data[1::2, :]
        chB = data[2::2, :]
        delta_steps = self.delta_steps(chA, chB)
        # get the reverse cumulative sum
        position_deltas = np.cumsum(delta_steps[::-1])[::-1]

        positions = last_position + position_deltas
        return positions

    def get_velocity(self):
        """Gets the velocity of the motor after calibration"""
        self.newport_lock.acquire(True)
        return self.instruments['newport'].get_velocity()
        self.newport_lock.release()

    def get_data(self, *args, **kwargs):
        """Returns the data variable with the result of the get_position function"""
        return self.get_position(*args, **kwargs)

    def get_target(self):
        if self.is_moving():
            return self.target_position
        else:
            return self.get_position()

    def stop(self):
        # first stop the position setting thread
        self.movement_stop.set()
        # stop the motors
        self.newport_lock.acquire(True)
        self.instruments['newport'].stop()
        self.newport_lock.release()
        # make sure the thread has finished and closed nicely
        if self.set_position_thread.is_alive():
            self.set_position_thread.join()

    def define_current_position(self, position, wait=True):
        """Defines the current position"""
        self.current_position_lock.acquire(True)
        self.current_position = position
        self.current_position_lock.release()
        self.newport_lock.acquire(True)
        self.instruments['newport'].define_current_position(
            position, wait=wait)
        self.newport_lock.release()

    def save_data(self, group, data):
        # get the columns for the data
        columns = list(self.instruments['newport'].motors.values())
        # get the data
        data_pd = pd.DataFrame(np.array(data)[None, :], columns=columns)
        # save the data
        with pd.HDFStore(group.file.filename) as store:
            store.append(group.name + '/data', data_pd, data_columns=True)
        return group

    def save(self, group, name=None, historical=False, start_time=0, end_time=-1, wait=True):
        return super().save(group, name=None, historical=False, start_time=0, end_time=-1, wait=True)

    def is_moving(self):
        return self.set_position_thread.is_alive()

    def wait(self):
        while True:
            time.sleep(0.05)
            if not self.is_moving():
                break

    def __exit__(self, *args):
        if self.set_position_thread.is_alive():
            self.stop()

        with warnings.catch_warnings(record=False):
            warnings.simplefilter("ignore")
            self.update_position_stop.set()
            self.update_position_thread.join()
        for inst in self.instruments.values():
            inst.__exit__(args)

