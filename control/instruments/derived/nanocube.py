from ..basic.ni_instrument import NIinst
import threading
import numpy as np
import copy
from data.signal_generation import stack_funs, get_const_signal
import pandas as pd


class NanoCube(NIinst):
    def __init__(self, *args, speed=100, **kwargs):
        """Creates nanocube instrument. It's a subclass of NIinst and accepts the same parameters, in addition to speed [um/s]"""
        self.speed = speed  # in um per s
        NIinst.__init__(self, *args, **kwargs)
        self.sliding_thread = threading.Thread()

        # TODO currently hardcoded, possibly move to settingsfile
        self.direction_labels = ['x', 'y', 'z']

    def is_in_range(self, position):
        data = pd.DataFrame([position])
        return self.calibration.is_in_range(data)

    # def get_allowed_positions(self):
    #     min_position = self.calibration.inst2data(pd.DataFrame([[0, 0, 0]])).values.T
    #     max_position = self.calibration.inst2data(pd.DataFrame([[10, 10, 10]])).values.T
    #     return np.hstack((min_position, max_position))

    def get_position(self):
        # gets the last sample read
        self.data_lock.acquire(True)
        try:
            #print('------------->', self.data_stream)
            # pos = copy.deepcopy(self.data_stream[-1][-1:])   # TODO from Luka, dont know why he does it like this
            pos = copy.deepcopy(self.data_stream[-1][1:])
            #print('------------->', pos)
        except IndexError:
            # if nothing in the data stream, means that you are at 0, 0, 0
            pos = pd.DataFrame(np.zeros((1, 3)), columns=self.ports.values())
        self.data_lock.release()
        #print(self.calibration.inst2data(pos))
        #return np.array(self.calibration.inst2data(pos))[0, :]   # TODO from Luka, dont know ...
        return np.array(self.calibration.inst2data(pos))

    def slide_to_position(self, position):
        """Moves continuously to the position with the given speed"""
        # get the current position
        current_pos = self.get_position()
        position = np.array(position)
        print(f'sliding {current_pos} -> {position}')
        # get delta
        delta_pos = current_pos - position
        duration = np.linalg.norm(delta_pos) / self.speed
        # create the signal
        signal = [None] * 3
        signal[0], full_time = stack_funs(
            [lambda t: np.linspace(current_pos[0], position[0], len(
                t)), lambda t: position[0] * np.ones(len(t))],
            [duration, 0.2])
        signal[1], full_time = stack_funs(
            [lambda t: np.linspace(current_pos[1], position[1], len(
                t)), lambda t: position[1] * np.ones(len(t))],
            [duration, 0.2])
        signal[2], full_time = stack_funs(
            [lambda t: np.linspace(current_pos[2], position[2], len(
                t)), lambda t: position[2] * np.ones(len(t))],
            [duration, 0.2])

        t0 = self.stage_data(signal, full_time)
        self.wait_for_time(t0 + duration)
        self.stage_data(get_const_signal(position), 1)

    def is_moving(self):
        return self.sliding_thread.is_alive()

    def set_position(self, position, wait=False, slide=True, relative=False):
        """ sets the position and slides there. If wait is true the program is blocked until the movement is finished.
         If slide is False, goes to position instantaneously (this might introduce shaking of the system)"""
        print('button action', position)
        #assert len(position) == 3   # TODO ???
        assert self.speed > 0 and self.speed < 1000, 'Speed should be between 0 and 1000'
        if relative:
            # TODO very ugly code
            #position = np.array(position)
            #current_position = self.get_position()
            #position += current_position
            current_position = self.get_position()
            map_coordinate_index = {
                'x': 0,
                'y': 1,
                'z': 2,
            }
            #print('current_position', current_position)
            for k, v in position.items():
                current_position[map_coordinate_index[k]] += v
            position = current_position
        if slide:
            if not self.is_moving():
                # start the position setting thread where the cube goes to the given position with the given speed
                self.sliding_thread = threading.Thread(
                    target=self.slide_to_position, args=(position,))
                self.sliding_thread.daemon = True
                self.sliding_thread.start()
            if wait:
                self.sliding_thread.join()
        else:
            self.stage_data(get_const_signal(position), 1)

    def home(self):
        """ 
        Slides nanocube to the home position, middle of the range.
        """
        self.set_position([0, 0, 0])
