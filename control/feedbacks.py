import numpy as np
# import pandas as pd
import pickle


class NIFeedbackController:
    def __init__(self, receiver_instrument, sender_instrument=None, setpoint=None, parameters=None, **kwargs):
        """
        Class defining the feedback.

        Args:
            receiver_instrument (list): instrument which is being feedback corrected. Needs to be an output instrument.
            sender_instrument (list, optional): instrument which is reading the feedback. Needs to be an input instrument.
            setpoint (dict, optional): dictionary of setpoints per output port. By default it's zeros
            parameters (list, optional): parameters for calculating the correction
        """
        assert receiver_instrument.port_type in {"AO", "DO"}

        self.output_ports = receiver_instrument.ports
        if sender_instrument is not None:
            assert sender_instrument.port_type in {"AI", "DI"}
            self.input_ports = sender_instrument.ports
        self.parameters = parameters
        self.setpoint = {port: np.zeros(1) for port in self.output_ports}

    def calculate_correction(self, setpoint, signal):
        """Function to calculate the feedback.
        Args:
            setpoint (dict): dictionary of setpoints for each output port for which to calculate the correction
            signal (dict): dictionary of read signal for each input port
        """
        return {port: 0 for port in self.output_ports}


class PIDfeedback(NIFeedbackController):

    def __init__(self, receiver_instrument, sender_instrument, parameters, setpoint=None):
        """
        Class defining the pid feedback. See NIFeedbackController.

        Args:
            receiver_instrument (list): instrument which is being feedback corrected. Needs to be an output instrument.
            sender_instrument (list, optional): instrument which is reading the feedback. Needs to be an input instrument.
            setpoint (dict, optional): dictionary of setpoints per output port. By default it's zeros
            parameters (dict): parameters for calculating the correction. Can contain:
                    "Kp": P coefficient. Default 0
                    "Ki": I coefficient. Default 0
                    "Kd": D coefficient. Default 0
        """
        NIFeedbackController.__init__(self, receiver_instrument, sender_instrument=sender_instrument, setpoint=setpoint,
                                      parameters=parameters)
        if "Kp" not in self.parameters:
            self.parameters["Kp"] = 0
        if "Ki" not in self.parameters:
            self.parameters["Ki"] = 0
        if "Kd" not in self.parameters:
            self.parameters["Kd"] = 0
        self.Kp, self.Ki, self.Kd = self.parameters["Kp"], self.parameters["Ki"], self.parameters["Kd"]
        # get the integration / differentiation time
        self.dt = sender_instrument.controller.output_refresh_time
        self.integral = 0
        self.previous_error = 0
        # with open('control\hyst_poly_coeff.p', 'rb') as f:
        #     self.poly_coeffs = pickle.load(f)
        # self.deriv_poly = np.poly1d(self.poly_coeffs['deriv'])

    def calculate_correction(self, setpoint, signal):
        """Function to calculate the feedback.
        Args:
            setpoint (dict): dictionary of setpoints for each output port for which to calculate the correction
            signal (dict): dictionary of read signal for each input port
        """
        # signal and setpoint should be dictionaries. Turn to numpy arrays
        setpoint_arr = np.vstack([v for v in setpoint.values()])
        signal_arr = np.vstack([v for v in signal.values])
        # calculate the gain
        # gain = np.array([self.deriv_poly(sg) for sg in signal_arr])
        gain = 1
        # calculate the error
        error = gain * (signal_arr - setpoint_arr)
        self.integral += self.dt * error
        derivative = (error - self.previous_error) / self.dt
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        # output_factor = np.array([self.deriv_poly(sg) for sg in signal_arr])
        # output = output_factor * output
        # output[output > 0.5] = 0.5
        # output[output < -0.5] = -0.5
        # update the previous error
        self.previous_error = error
        # return the dictionary as required
        return {port: output[i, :] for i, port in enumerate(self.output_ports)}
