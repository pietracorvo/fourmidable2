from math import pi
import numpy as np
import pandas as pd
from warnings import warn


class InstrumentCalibration:
    """Basic calibration class.
    All calibrations contain two functions:
        inst2data for converting from the raw readings to calibrated data
                (e.g. for hallprobes from volts read to mT)
        data2inst for converting from the data given to the instrument to the units the instrument can use
                (e.g. for hexapole from mT to V to apply to kepcos)
    Args:
        parameters (optional): parameters of calibration.
                               Note, if you want them saved when instrument is saved, need to be in numerical format
        subinstruments (optional): other instruments the calibration is dependent on.
                                    E.g. stage for putting stuff in the frame of reference of the stage
        """

    def __init__(self, parameters=None, subinstruments=None):
        self.parameters = parameters
        self.subinstruments = subinstruments

    def inst2data(self, data, **kwargs):
        return data

    def data2inst(self, data, **kwargs):
        return data


class ScaleCalib(InstrumentCalibration):
    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)

    def data2inst(self, data):
        return np.array(data) / np.array(self.parameters)

    def inst2data(self, data):
        return np.array(data) * np.array(self.parameters)


class ScaleCalib1D(InstrumentCalibration):
    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)

    def data2inst(self, data):
        if isinstance(data, list):
            data = data[0]
        return data * self.parameters

    def inst2data(self, data):
        if isinstance(data, list):
            data = data[0]
        return data / self.parameters


class TemperatureCalibration(InstrumentCalibration):
    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)
        self.offset = self.parameters['offset']
        self.scale = self.parameters['scale']

    def inst2data(self, data):
        if data.shape[0] == 0:
            return data
        data *= self.offset
        data += self.scale
        return data

    def data2inst(self, data):
        if data.shape[0] == 0:
            return data
        data -= self.offset
        data /= self.scale
        return data


class Reference(InstrumentCalibration):
    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)
        self.offset = self.parameters['offset']

    def data2inst(self, data):
        """Always outputs the offset value, no matter what is staged"""
        return pd.DataFrame().reindex_like(data).fillna(value=self.offset)


class NIoffsetScale(InstrumentCalibration):
    """Offset and scales the data by the given parameters. Accepts both numbers and matrices/vectors for offset"""

    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)
        if 'offset' in self.parameters:
            self.offset = np.array(self.parameters['offset'])
        else:
            self.offset = np.array([0] * len(self.parameters['scale']))
        self.scale = np.array(self.parameters['scale'])
        if self.scale.ndim == 0:
            self.scale = self.scale[None, None]

    def data2inst(self, data):
        if data.shape[0] == 0:
            return data
        data_calib = pd.DataFrame(np.array(data - self.offset).dot(np.linalg.inv(np.transpose(self.scale))),
                                  columns=data.columns,
                                  index=data.index)
        return data_calib

    def inst2data(self, data):
        if data.shape[0] == 0:
            return data
        data_calib = pd.DataFrame(np.array(data).dot(np.transpose(self.scale)) + self.offset, columns=data.columns,
                                  index=data.index)
        return data_calib


class StageSampleRefCalib(InstrumentCalibration):
    def __init__(self, parameters, subinstruments):
        """Calibrates the stage movement in the sample reference frame and eucentric calibration
        Parameters should contain zero_angle and rotation_axis_displacement (which are both assumed to be 0 if not provided)"""
        # get only the pi stage
        rotation_stage = subinstruments.instruments['pi_rotator']
        InstrumentCalibration.__init__(
            self, parameters, subinstruments=rotation_stage)
        if "zero_angle" not in self.parameters:
            self.parameters["zero_angle"] = 0
        if "rotation_axis_displacement" not in self.parameters:
            self.parameters["rotation_axis_displacement"] = np.array([0, 0, 0])
            self.rot_ax_disp = self.parameters["rotation_axis_displacement"]
        else:
            self.rot_ax_disp = np.array(
                self.parameters["rotation_axis_displacement"])
        if "zero_position_displacement" not in self.parameters:
            self.parameters["zero_position_displacement"] = np.array([0, 0, 0])
            self.zero_position_disp = self.parameters["zero_position_displacement"]
        else:
            self.zero_position_disp = np.array(
                self.parameters["zero_position_displacement"])
        self.angle = self.parameters['zero_angle']

    def get_matrix(self, data_angle):
        """get the rotation matrix"""
        angle = np.radians(self.angle + data_angle)
        c, s = np.cos(angle), np.sin(angle)
        R = np.array(((c, s), (-s, c)))
        return R

    def inst2data(self, data, eucentric=True):
        data = np.array(data)
        if eucentric:
            data_angle = data[3]
            R = self.get_matrix(data_angle)
        else:
            data_angle = self.subinstruments.get_data()
            R = self.get_matrix(data_angle)

        data[[0, 2]] = R.transpose().dot(
            data[[0, 2]] - self.rot_ax_disp) + self.rot_ax_disp + self.zero_position_disp
        return list(data)

    def data2inst(self, data, eucentric=True):
        data = np.array(data)
        if eucentric:
            data_angle = data[3]
            R = self.get_matrix(data_angle)
        else:
            data_angle = self.subinstruments.get_data()
            R = self.get_matrix(data_angle)
        # rotate the xy coordinates
        data[[0, 2]] = R.dot(
            data[[0, 2]] - self.rot_ax_disp - self.zero_position_disp) + self.rot_ax_disp
        return list(data)


class NewportCalib(InstrumentCalibration):
    """Converts between motor ticks and the physical values using parameters.
    If phys2ticks is True, the conversion goes from physical values to ticks. Otherwise, it is the other way around."""

    def __init__(self, parameters):
        InstrumentCalibration.__init__(self, parameters)

    def inst2data(self, data):
        return [v / p for v, p in zip(data, self.parameters)]

    def data2inst(self, data):
        return [v * p for v, p in zip(data, self.parameters)]


class SampleFieldsCalib(InstrumentCalibration):
    def __init__(self, parameters, subinstruments):
        # get only the pi stage
        stage = subinstruments
        InstrumentCalibration.__init__(
            self, parameters, subinstruments=stage)
        self.magnet_to_voltage = -1
        # rotation matrix to go between the magnet and table coordinate systems
        self.table_to_magnet = np.sqrt(1 / 6) * np.array(
            [[-2, 1, 1], [-np.sqrt(2), -np.sqrt(2), -np.sqrt(2)], [0, -np.sqrt(3), np.sqrt(3)]])
        # the angle at which the stage coordinate system is aligned with the axis of the table
        self.zero_angle = parameters['zero_angle']

    def get_stage_angle(self):
        """Gets the position of the stage with respect to the table coordinate system in radians"""
        angle = self.subinstruments.get_data()[3]
        return np.radians(angle - self.zero_angle)

    def get_sample_to_voltage(self):
        """"get the rotation matrix"""
        angle = self.get_stage_angle()
        c, s = np.cos(angle), np.sin(angle)
        sample_to_table = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
        return sample_to_table.dot(self.table_to_magnet) * self.magnet_to_voltage

    def inst2data(self, data):
        if data.shape[0] == 0:
            return data
        R = self.get_sample_to_voltage()
        data_calib = data.dot(np.linalg.inv(R))
        if isinstance(data_calib, pd.Series):
            data_calib = data_calib.to_frame()
        data_calib.columns = data.columns
        return data_calib

    def data2inst(self, data):
        if data.shape[0] == 0:
            return data
        R = self.get_sample_to_voltage()
        data_calib = data.dot(R)
        if isinstance(data_calib, pd.Series):
            data_calib = data_calib.to_frame()
        data_calib.columns = data.columns
        return data_calib


class NanoCubeCalib(NIoffsetScale):
    def __init__(self, parameters):
        InstrumentCalibration.__init__(
            self, parameters)
        self.offset = np.array(self.parameters['offset'])
        self.scale = np.array(self.parameters['scale'])

    def data2inst(self, data):
        if data.shape[0] == 0:
            return data
        data_calib = self.scale * data + self.offset
        if (data_calib > 10).any(axis=None) or (data_calib < 0).any(axis=None):
            warn('Nanocube out of range!')
            data_calib[data_calib > 10] = 10
            data_calib[data_calib < 0] = 0
            return data_calib * 0
        return data_calib

    def is_in_range(self, data):
        if data.shape[0] == 0:
            return False
        data_calib = self.scale * data + self.offset
        if (data_calib > 10).any(axis=None) or (data_calib < 0).any(axis=None):
            return False
        else:
            return True

    def inst2data(self, data):
        if data.shape[0] == 0:
            return data
        data_calib = (data - self.offset) / self.scale
        return data_calib


class HPSampleCalib(InstrumentCalibration):
    """Offset and scales the data by the given parameters. Accepts both numbers and matrices/vectors for offset"""

    def __init__(self, parameters):

        InstrumentCalibration.__init__(self, parameters)
        if 'offset' in self.parameters:
            self.offset = np.array(self.parameters['offset'])
        else:
            self.offset = np.array([0] * len(self.parameters['scale']))
        self.scale = np.array(self.parameters['scale'])

        if 'angle_senis2table' in parameters:
            self.angle_senis2table = float(self.parameters['angle_senis2table'])
        else:
            self.angle_senis2table = 0

        if self.scale.ndim == 0:
            self.scale = self.scale[None, None]

    def get_senis2table_matrix(self):
        """Get matrix that rotates the FOR of the senis into table FOR"""
        angle = self.angle_senis2table * np.pi/180
        c, s = np.cos(angle), np.sin(angle)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        return R

    def data2inst(self, data):
        if data.shape[0] == 0:
            return data
        # get the matrix to rotate senis FOR to table FOR
        R = self.get_senis2table_matrix()
        data_calib = pd.DataFrame((np.array(data).dot(np.linalg.inv(R)) - self.offset).dot(np.linalg.inv(np.transpose(self.scale))),
                                  columns=data.columns,
                                  index=data.index)
        return data_calib

    def inst2data(self, data):
        if data.shape[0] == 0:
            return data
        # get the matrix to rotate senis FOR to table FOR
        R = self.get_senis2table_matrix()
        # combine the transformations
        M = np.transpose(self.scale).dot(R)
        off = self.offset.dot(R)
        data_calib = pd.DataFrame(np.array(data).dot(M) + off, columns=data.columns,
                                  index=data.index)
        return data_calib


class SmaractScaleCalib(InstrumentCalibration):
    """Offset and scales the data by the given parameters. Accepts both numbers and matrices/vectors for offset"""

    def __init__(self, parameters):
        InstrumentCalibration.__init__(
            self, parameters)
        assert isinstance(self.parameters['scale'], list)
        self.scale = np.array(self.parameters['scale'])

    def data2inst(self, data):
        data_calib = [s * dt for s, dt in zip(self.scale, data)]
        return data_calib

    def inst2data(self, data):
        data_calib = [dt / s for s, dt in zip(self.scale, data)]
        return data_calib


class SmaractSampleCalib(InstrumentCalibration):
    """Offset and scales the data by the given parameters. Accepts both numbers and matrices/vectors for offset"""

    def __init__(self, parameters):
        InstrumentCalibration.__init__(
            self, parameters)
        assert isinstance(self.parameters['scale'], list)
        self.scale = np.array(self.parameters['scale'])

    def get_table2sample_matrix(self, angle):
        c, s = np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        return R

    def data2inst(self, data):
        R = self.get_table2sample_matrix(data[3])
        data_calib = np.array(data)
        data_calib[:3] = data_calib[:3].dot(R.T)
        data_calib = np.array(
            [s * dt for s, dt in zip(self.scale, data_calib)])
        return data_calib

    def inst2data(self, data):
        data_calib = np.array([dt / s for s, dt in zip(self.scale, data)])
        R = self.get_table2sample_matrix(data_calib[3])
        data_calib[:3] = data_calib[:3].dot(R)
        return data_calib
