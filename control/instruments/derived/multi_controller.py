from control.instruments.basic import Instrument, np
from control import load_from_settings as load
import time
import json
import os
import threading
import traceback
import pandas as pd
from shutil import copyfile


class MultiController(Instrument):
    def __init__(self, *, controller, subinstruments, directions=None, **kwargs):
        Instrument.__init__(self, controller=controller, **kwargs)

        # load instruments
        self.instruments = load.load_instruments(
            self, subinstruments, controller)
        # add direction
        self.directions = directions

        # make a list of directions
        self.direction_labels = dict()
        for inst, dir in self.directions.items():
            if isinstance(dir, list):
                self.direction_labels.update({d: inst for d in dir})
            else:
                self.direction_labels[dir] = inst

        # check if there is a file with the last position saved
        self.save_position_file_name = os.path.dirname(
            __file__) + '\\last_position.json'
        try:
            with open(self.save_position_file_name, 'r') as file:
                last_position = json.load(file)
                self.define_current_position(
                    self.calibration.inst2data(last_position))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        # open the temp file for quicker saving
        self.temp_name = os.path.dirname(
            __file__) + '\\~temp_pos.json'
        # define the save position thread and start it
        self.save_position_thread = threading.Thread(
            target=self.save_position_worker)
        self.save_position_thread.daemon = True
        self.save_position_lock = threading.Lock()
        self.stop_saving_event = threading.Event()
        # define the saving position period
        self.saving_position_period = 0.5
        # get position lock
        self.get_position_lock = threading.Lock()
        self.save_position_thread.start()

    def save_position(self):
        with open(self.temp_name, 'w') as file:
            self.save_position_lock.acquire(True)
            position = self.get_raw_position()
            file.seek(0)
            file.truncate()
            json.dump(position, file)
            self.save_position_lock.release()
        copyfile(self.temp_name, self.save_position_file_name)

    def save_position_worker(self):
        while not self.stop_saving_event.is_set():
            time.sleep(self.saving_position_period)
            try:
                self.save_position()
            except:
                print('Cant save the last position to the file')
                traceback.print_exc()

    def define_current_position(self, position, **kwargs):
        """Defines the current position of the axes. This is for defining zero of our coordinate system."""
        # move to the desired position
        cal_position = self.calibration.data2inst(position, **kwargs)
        for key in self.instruments:
            # get the position vector
            try:
                p = [cal_position.pop(0)
                     for i in range(len(self.directions[key]))]
                self.instruments[key].define_current_position(p)
            except IndexError:
                raise IndexError(
                    'The last position file does not have the correct number of entries!')

    def get_raw_position(self):
        """Gets the position before calibration"""
        self.get_position_lock.acquire(True)
        data = []
        for inst in self.instruments.values():
            inst_data = inst.get_position()
            # add the data to data array
            if isinstance(inst_data, list):
                data += inst_data
            else:
                data += [inst_data]
        self.get_position_lock.release()
        return data

    def get_position(self, **kwargs):
        data = self.get_raw_position()
        calibrated_data = self.calibration.inst2data(data, **kwargs)
        return calibrated_data

    def get_target(self, **kwargs):
        """Gets the target position"""
        data = []
        for inst in self.instruments.values():
            inst_data = inst.get_target()
            # add the data to data array
            if isinstance(inst_data, list):
                data += inst_data
            else:
                data += [inst_data]
        calibrated_data = self.calibration.inst2data(data, **kwargs)
        return calibrated_data

    def get_data(self, *args, **kwargs):
        """Returns the data variable with the result of the get_position function"""
        return self.get_position(*args, **kwargs)

    def set_position(self, position, direction='all', relative=False, wait=False, **kwargs):
        """Moves to the set position, direction can be specified as a string from direction_labels property, or as an index of the direction"""
        if direction == 'all':
            precal_position = position
        else:
            # get current position (need to do it this way to go through the current calibration)
            if relative:
                precal_position = [0] * len(self.direction_labels)
            else:
                precal_position = self.get_data()
            # update the desired axis
            if isinstance(direction, str):
                indx = list(self.direction_labels.keys()).index(direction)
                precal_position[indx] = position
            else:
                precal_position[direction] = position

        if relative:
            current_position = self.get_position(**kwargs)
            precal_position = [p + q for p,
                               q in zip(precal_position, current_position)]
        # get move position
        move_position = self.calibration.data2inst(precal_position, **kwargs)
        # move to the desired position
        for key in self.instruments:
            # get the position vector
            p = [move_position.pop(0)
                 for i in range(len(self.directions[key]))]
            self.instruments[key].set_position(p, relative=False, wait=wait)

    def is_moving(self):
        """Gets a list of bools corresponding to directions saying if there is movement in that direction"""
        moving = []
        for inst in self.instruments.values():
            inst_moving = inst.is_moving()
            if isinstance(inst_moving, list):
                moving += inst_moving
            else:
                moving.append(inst_moving)
        return any(moving)

    def stop(self):
        """Stops whatever the instrument is doing"""
        for inst in self.instruments.values():
            inst.stop()
        # save the current position
        position = []
        for inst in self.instruments.values():
            inst_data = inst.get_position()
            # add the data to data array
            if isinstance(inst_data, list):
                position += inst_data
            else:
                position += [inst_data]
        self.save_position()

    def wait(self):
        """Waits for the movement to finish"""
        while True:
            time.sleep(0.1)
            if not self.is_moving():
                break

    def save_data(self, group, data):
        # get the data
        data = pd.DataFrame(
            np.array(data)[None, :], columns=self.direction_labels)
        # save the data
        with pd.HDFStore(group.file.filename) as store:
            store.append(group.name + '/data', data, data_columns=True)

    def __exit__(self, *args):
        self.stop_saving_event.set()
        self.save_position_thread.join()
        for inst in self.instruments.values():
            inst.__exit__(args)


# simple test of the stage
if __name__ == '__main__':
    from control.instruments.moke import Moke

    moke = Moke()
    try:
        stage = moke.instruments['Stage']
        position = stage.get_position()
        print('Position: ', position)
        position[0] += 20
        stage.set_position(position, wait=True)
        print('position set')

    finally:
        moke.stop()
