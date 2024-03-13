import os
import queue
import threading
import time
import copy
import numpy as np
import usb.backend.libusb1
from . import newport_interface
import warnings

usb.core.find(backend=usb.backend.libusb1.get_backend(
    find_library=lambda x: os.path.dirname(__file__) + "\\libusb-1.0.dll"))


# TODO: document this
class NewportControl:
    def __init__(self, productid, vendorid, motors, name='', buffer_time=0.05):
        self.name = name
        # connect to the device
        self.interface = newport_interface.Controller(productid, vendorid)
        self.buffer_time = buffer_time
        self.motors = motors

        self.command_queue = queue.Queue()
        self.command_lock = threading.Lock()
        self.command_thread = threading.Thread(target=self.command_worker)
        self.command_thread.daemon = True
        self.command_thread_stop = threading.Event()

        self.position_displacement = {m: 0 for m in motors}

    def start_thread(self):
        if not self.command_thread.is_alive():
            self.command_thread_stop.clear()
            motors = copy.deepcopy(self.motors)
            self.command_thread = threading.Thread(
                target=self.command_worker, args=(motors,))
            self.command_thread.daemon = True
            self.command_thread.start()

    def command_worker(self, motors):
        while not self.command_thread_stop.is_set():
            try:
                command = self.command_queue.get(block=False)
            except queue.Empty:
                break
            self.command_lock.acquire(True)
            self.interface.command(command)
            self.command_lock.release()
            # check if motion done before proceeding
            for m in motors:
                while True:
                    self.command_lock.acquire(True)
                    if int(self.interface.command(m + 'MD?').split('>')[1]) or self.command_thread_stop.is_set():
                        self.command_lock.release()
                        break
                    self.command_lock.release()
                    time.sleep(self.buffer_time)
        self.command_thread_stop.clear()

    def set_position(self, position, motor, relative=False, wait=False):
        """Queues the motor movement to the given position"""
        if motor not in self.motors:
            warnings.warn(
                'The given motor is not one of the motors in the given set of the controller! This might lead to unexpected results. Please add the motor to the controller in the settings',
                Warning)
        if relative:
            self.command_queue.put(motor + 'PR' + str(int(position)))
        else:
            self.command_queue.put(
                motor + 'PA' + str(int(position + self.position_displacement[motor])))
        self.start_thread()

        if wait:
            self.wait()

    def define_current_position(self, position, motor):
        """Defines the home with respect to the current position"""
        # get the current position
        self.command_lock.acquire(True)
        motor_position = int(self.interface.command(
            motor + 'TP?').split('>')[1])
        self.command_lock.release()
        # save the difference
        self.position_displacement[motor] = motor_position - position

    def set_velocity(self, velocity, motor):
        """Queues the velocity setting"""
        self.command_queue.put(motor + 'VA' + str(int(velocity)))
        self.start_thread()

    def get_position(self, motor):
        """Gets the current position of the motor after calibration"""
        self.command_lock.acquire(True)
        position_str = self.interface.command(motor + 'TP?')
        self.command_lock.release()
        # turn the output format to number
        position = int(position_str.split('>')[1])
        # add the displacement
        return position - self.position_displacement[motor]

    def get_velocity(self, motor):
        """Gets the velocity of the motor"""
        self.command_lock.acquire(True)
        vel_str = self.interface.command(motor + 'VA?')
        self.command_lock.release()
        # turn the output format to number
        vel = int(vel_str.split('>')[1])
        return vel

    def time_to_position(self, position, motor, relative=False):
        """Calculates the time required to travel to the given position in seconds"""
        if relative:
            difference = position
        else:
            difference = position - self.get_position(motor)
        velocity = self.get_velocity(motor)
        t = np.abs(difference / velocity) + self.buffer_time
        return t

    def stop(self):
        self.command_queue.empty()
        self.command_thread_stop.set()
        try:
            self.command_thread.join()
        except RuntimeError:
            pass
        for m in self.motors:
            self.interface.command(m + 'ST')
        # restart the thread
        self.start_thread()

    def command_time(self, command):
        m = newport_interface.NEWFOCUS_COMMAND_REGEX.match(command)
        # Extract matched components of the command
        motor, command, parameter = m.groups()
        if command == 'PA':
            return self.time_to_position(int(parameter), motor, relative=False)
        elif command == 'PR':
            return self.time_to_position(int(parameter), motor, relative=True)
        else:
            return self.buffer_time

    def get_target(self, motor):
        """Gets the target position"""
        self.command_lock.acquire(True)
        position_str = self.interface.command(motor + 'PA?')
        self.command_lock.release()
        # turn the output format to number
        position = int(position_str.split('>')[1])
        return position - self.position_displacement[motor]

    def wait(self):
        """Waits until all the commands are executed"""
        if self.command_thread.is_alive():
            self.command_thread.join()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.is_busy():
            self.stop()

    def is_busy(self):
        return self.command_thread.is_alive()


def list_usbs():
    """Prints the vendor and product ids of all usb devices found, useful for finding the product ids and vendor ids
    of devices to connect"""
    dev = usb.core.find(find_all=True)
    for cfg in dev:
        print(usb.util.get_string(cfg, cfg.iProduct))
        print('Decimal VendorID=' + str(cfg.idVendor) +
              ' & ProductID=' + str(cfg.idProduct) + '\n')
        print('Hexadecimal VendorID=' + hex(cfg.idVendor) +
              ' & ProductID=' + hex(cfg.idProduct) + '\n\n')
