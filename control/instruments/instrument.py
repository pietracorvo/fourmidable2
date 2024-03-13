from ..controllers import *
import weakref
from ..exceptions import ClosingAll
from control.calibration import *


class Instrument:
    """A class template for instruments

    Args:
        name (str) : Human readable name of the instrument
        controller (object) : an object defined in the controllers.py module
        calibration (function) : a handle to a function used for converting input/output data into/from physically
                                meaningful quantities. Default is identity.
        parent (object) : parent instrument, used if an instrument is a subinstrument of a superinstrument
    """

    def __init__(self, name='', controller=None, calibration=None, parent=None):
        """Assigns the class attributes given as keyword parameters. Otherwise a default is assigned"""
        assert isinstance(name, str)
        self.name = name
        self.controller = controller
        if parent is None:
            self.parent = parent
        else:
            self.parent = weakref.ref(parent)

        if (calibration is not None) and (calibration != "default"):
            assert isinstance(calibration, InstrumentCalibration)
            self.calibration = calibration
        else:
            self.calibration = InstrumentCalibration()

    def get_data(self, *args, **kwargs):
        """Gets the instrument data"""
        return None

    def create_save_group(self, group, name=None, additional=None):
        """Creates a group to save in, together with information about the type of instrument,
        controller, and any other information given in a dictionary additional"""
        if name is None:
            inst_group = group.create_group(self.name)
        else:
            inst_group = group.create_group(name)
        inst_group.attrs['type'] = self.__class__.__name__
        # save the controller (or multiple controllers)
        if isinstance(self.controller, list):
            # list of controllers
            for i, cont in enumerate(self.controller):
                inst_group.attrs['controller'+str(i)] = cont.__class__.__name__
                inst_group.attrs['controller' + str(i) + '_name'] = cont.name.encode('utf8')
        elif isinstance(self.controller, dict):
            # list of controllers
            for i, cont in enumerate(self.controller.values()):
                inst_group.attrs['controller'+str(i)] = cont.__class__.__name__
                inst_group.attrs['controller' + str(i) + '_name'] = cont.name.encode('utf8')
        else:
            inst_group.attrs['controller'] = self.controller.__class__.__name__
            inst_group.attrs['controller_name'] = self.controller.name.encode('utf8')
        if additional is not None:
            for key, value in additional.items():
                inst_group.attrs[key] = value
        # save the calibration
        if self.calibration.parameters is not None:
            calib_grp = inst_group.create_group('calibration')
            calib_grp.attrs['type'] = type(self.calibration).__name__
            if isinstance(self.calibration.parameters, dict):
                for key, value in self.calibration.parameters.items():
                    if isinstance(value, str):
                        calib_grp.attrs[key] = value
                        continue
                    if not isinstance(value, list) and not isinstance(value, np.ndarray):
                        value = np.array([value])
                    calib_grp.create_dataset(key, data=value)
                if hasattr(self, 'instruments'):
                    try:
                        for inst in self.instruments.values():
                            inst.create_save_group(calib_grp)
                    except:
                        traceback.print_exc()
            else:
                try:
                    calib_grp.create_dataset(
                        'calibration_parameters', data=np.array(self.calibration.parameters))
                except:
                    pass
        return inst_group

    def save_data(self, group, data):
        dset = group.create_dataset('data', data=data)
        return dset

    def save(self, group, name=None, additional=None, **kwargs):
        # create save group
        inst_group = self.create_save_group(group, name, additional)
        # get the data
        data = self.get_data(**kwargs)
        # save the data
        self.save_data(inst_group, data)

    def stop(self):
        """Function to stop an instrument after which the instrument should be safe to delete"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # if there is a closing all exception, we are assuming that the controller is going to solve nice closing to
        # save time. If this is not the case, override this method.
        if len(args) == 0 or isinstance(args[0], ClosingAll):
            self.stop()

