import hjson
import os
from control.instruments.basic import *
from control.instruments.derived import *
import control.calibration as calibrationLib
from control.controllers import *
import control.feedbacks as feedbackLib
import traceback


def read_settings(path=None):
    """Opens and reads the settings file"""
    # get the settings file if it is None
    if path is None:
        project_dir = os.path.dirname(__file__).split(
            '\\')[:-1] + ['settings_file.hjson']
        path = '\\'.join(project_dir)

    with open(path, 'r') as file:
        settings_data = hjson.load(file)

    return settings_data


def load_controllers(controller_settings):
    """Initialises the controllers from settings"""
    controller = dict()
    for cont in controller_settings:
        # try loading each of controllers, say where the error is
        key = cont["name"]
        try:
            controller[key] = globals()[cont["type"]](
                name=key, **cont["parameters"])
            print('Connected to controller ' + key)
        except Exception as e:
            traceback.print_exc()
            print('Could not initialise controller ' + key + ': ', str(e))
    return controller


def load_instruments(parent, instrument_settings, controllers):
    """Loads the instruments from instrument settings and previously loaded controllers"""
    instruments = dict()
    calibrations = []
    feedbacks = dict()
    # add name as the parameter for simplicity (also legacy)
    for name in instrument_settings:
        instrument_settings[name]["name"] = name
    for inst in instrument_settings.values():
        try:
            # get type, the controller and calibration and remove them from the dictionary (for passing parameters after)
            inst_type = inst.pop("type")
            controller_key = inst.pop("controller")
            if "calibration" in inst:
                calibrations.append(inst.pop("calibration"))
            else:
                calibrations.append("default")
            # check if feedback added to the instrument
            if "feedback" in inst:
                feedbacks.update({inst["name"]: inst.pop("feedback")})
            # we are supporting multiple controllers per device
            if isinstance(controller_key, str):
                controller = controllers[controller_key]
            else:
                # create the instrument
                controller = {k: controllers[k] for k in controller_key}
            instruments[inst["name"]] = globals()[inst_type](
                controller=controller, parent=parent, **inst)
        except Exception as e:
            traceback.print_exc()
            print('Could not initialise instrument ' +
                  inst["name"] + ': ' + str(e))

    # iterate through all the instruments again and assign the corresponding calibrations. This has to be done in this
    # order to allow for passing of subinstruments to calibrations
    for inst, calib in zip(instrument_settings.values(), calibrations):
        try:
            if calib == "default":
                # calibration is default and has already been set by the instrument
                continue
            assert isinstance(calib, dict)
            # get the calibration
            calibration_string = calib["type"]
            if calibration_string != 'default':
                # create the calibration class
                if "parameters" in calib:
                    parameters = calib["parameters"]
                else:
                    parameters = None
                if "subinstruments" in calib:
                    subinstrument_names = calib["subinstruments"]
                    if isinstance(subinstrument_names, str):
                        subinstruments = instruments[subinstrument_names]
                    else:
                        subinstruments = []
                        for nm in subinstrument_names:
                            subinstruments.append(instruments[nm])
                else:
                    subinstruments = None
                if subinstruments is None and parameters is None:
                    instruments[inst["name"]].calibration = getattr(
                        globals()["calibrationLib"], calibration_string)()
                elif subinstruments is None:
                    instruments[inst["name"]].calibration = getattr(globals()["calibrationLib"], calibration_string)(
                        parameters)
                elif parameters is None:
                    instruments[inst["name"]].calibration = getattr(globals()["calibrationLib"], calibration_string)(
                        subinstruments)
                else:
                    instruments[inst["name"]].calibration = getattr(globals()["calibrationLib"], calibration_string)(
                        parameters, subinstruments)

        except Exception as e:
            traceback.print_exc()
            print('Could not initialise calibration ' +
                  inst["name"] + ': ' + str(e))

    # go through all the feedbacks and create feedback classes and add them to the corresponding controllers
    for key, fb in feedbacks.items():
        try:
            # get the input and output instruments
            input_name = fb.pop("input_instruments")
            sender_instrument = instruments[input_name]
            receiver_instrument = instruments[key]
            feedback_type = fb.pop("type")
            feedback_controller = getattr(globals()["feedbackLib"], feedback_type)(
                receiver_instrument, sender_instrument=sender_instrument, **fb)
            # add feedback receivers and feedback senders. For this, the instrument has to have add_feedback_(sender/receiver) functions
            reader = sender_instrument.add_feedback_sender()
            receiver_instrument.add_feedback_receiver(
                feedback_controller, reader)

        except Exception as e:
            traceback.print_exc()
            print('Could not initialise feedback ' +
                  key + ': ' + str(e))

    return instruments
