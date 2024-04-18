from control.load_from_settings import load_instruments, load_controllers, read_settings
from .basic import Instrument
import copy
import datetime
from ..exceptions import ClosingAll
import warnings
import traceback
from control.instruments.basic.camera import Camera
from data.signal_generation import get_zeros_signal
# CODE MODIFIED
#from experiments.basic import zero_magnet, switch_laser
from experiments.basic import zero_magnet
import numpy as np

# this is for tracing prints, sometimes useful
# import sys
# class TracePrints(object):
#     def __init__(self):
#         self.stdout = sys.stdout

#     def write(self, s):
#         self.stdout.write("Writing %r\n" % s)
#         traceback.print_stack(file=self.stdout)


# sys.stdout = TracePrints()


class Moke(Instrument):
    def __init__(self, settings_data=None):
        # initialises all elements of the 3D moke

        Instrument.__init__(self)

        self.name = "3DMOKE"

        # get and save the settings for later reference
        self.settings_data = settings_data if settings_data is not None else copy.copy(read_settings())
        # load controllers
        self.controller = load_controllers(self.settings_data["controllers"])
        # load instruments
        self.instruments = load_instruments(
            self, self.settings_data["instruments"], self.controller)

        # start the NI controllers
        self.start()

    def start(self):
        # set the temperature reference signal
        try:
            # this also starts the first NI card
            self.instruments["reference"].stage_data(
                lambda x: np.zeros(len(x)), 1, autostart=True)
            print('NI card started')
            # start the laser
            # CODE MODIFIED
            #switch_laser(self, True)
        except KeyError:
            traceback.print_exc()
        # set the magnets to 0
        try:
            # this starts the second NI card
            zero_magnet(self)
            # make sure that the magnet instrument is running
            while not self.instruments["hexapole"].controller.is_running():
                time.sleep(0.05)
        except KeyError:
            pass
        # set the nanocube to 0
        try:
            # modified by alexander
            # self.instruments["nanocube"].home()
            self.instruments["stage"].home()
        except KeyError:
            pass

    # TODO: why pipython gives an exception here?
    def stop(self, err=None):
        if err not in {None, "dangerous_temperature", "outputs"}:
            warnings.warn("err not recognised, stopping all controllers")
        if err == "dangerous_temperature":
            # stop only the magnet
            try:
                self.instruments['hexapole'].stop()
            except KeyError:
                print('Hexapole not found. Stopping everything')
                self.stop()
        elif err == "outputs":
            # stop everything except the NIinputs and the camera
            for inst in self.instruments.values():
                if not isinstance(inst, Camera):
                    inst.stop()
        else:
            print('Stopping all controllers!')
            for key, cont in self.controller.items():
                try:
                    cont.stop()
                except:
                    traceback.print_exc()

    def save(self, group, name=None):
        """Iterates through all of the instruments and saves them with their respective methods"""
        group.attrs['type'] = self.__class__.__name__
        group.attrs['timestamp'] = datetime.datetime.now().isoformat()
        for key, inst in self.instruments.items():
            inst.save(group)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        print('Exiting moke')
        for key, inst in self.instruments.items():
            try:
                inst.__exit__(ClosingAll)
            except:
                traceback.print_exc()
        for key, cont in self.controller.items():
            try:
                cont.__exit__(ClosingAll)
            except:
                traceback.print_exc()


if __name__ == '__main__':
    mk = Moke()
