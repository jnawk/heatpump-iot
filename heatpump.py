"""Heatpump module"""
import subprocess

_A = 'action'
_C = 'command'

START_COOLING = {_A: 'cooling', _C: 'maxcold'}
SHUTDOWN = {_A: 'shutdown', _C: 'stokesoff'}
START_HEATING = {_A: 'heating', _C: 'stokesheat'}

H1 = 'heating_start'
H0 = 'heating_stop'
C0 = 'cooling_stop'
C1 = 'cooling_start'

_NEEDS_SET = '%s needs to be set'
_BACKWARDS = '%s needs to be less than %s'

class Heatpump(object):
    """Heatpump class"""
    def __init__(self):
        self._setpoints = {H1: None,
                           H0: None,
                           C0: None,
                           C1: None}
       self._current_action = None

    @property
    def setpoints(self):
        """Returns the setpoints"""
        return self._setpoints

    @property
    def _current_action(self):
        return _current_action

    @setpoints.setter
    def setpoints(self, setpoints):
        """Updates the setpoints"""
        target = {H1: setpoints[H1] if setpoints.has_key(H1) else self._setpoints[H1],
                  H0: setpoints[H0] if setpoints.has_key(H0) else self._setpoints[H0],
                  C0: setpoints[C0] if setpoints.has_key(C0) else self._setpoints[C0],
                  C1: setpoints[C1] if setpoints.has_key(C1) else self._setpoints[C1]}

        for param in [H0, H1, C0, C1]:
            if target[param] is None:
                raise ValueError(_NEEDS_SET % param)

        for params in [(H1, H0), (C0, C1), (H0, C0)]:
            if target[params[0]] >= target[params[1]]:
                raise ValueError(_BACKWARDS % params)

        self._setpoints = target

    def get_action(self, temperature):
        """Computes the action to take based on the current temperature"""
        if self._is_hot(temperature):
            return START_COOLING

        if self._is_cold(temperature):
            return START_HEATING

        if self._is_shutdown(temperature):
            return SHUTDOWN

        return None

    @staticmethod
    def send_command(command):
        """sends a command to the heatpump"""
        if subprocess.call(["irsend", "SEND_ONCE", "heat_pump", command[_C]]):
            self._current_action = command[_A]
        else:
            raise subprocess.CalledProcessError()

    def _is_hot(self, temperature):
        return self._has_cooling() and temperature > self._setpoints[C1]

    def _is_cold(self, temperature):
        return self._has_heating() and temperature < self._setpoints[H1]

    def _is_shutdown(self, temperature):
        if self._has_full_config():
            return temperature > self._setpoints[H0] and temperature < self._setpoints[C0]

        if self._has_heating() and temperature > self._setpoints[H0]:
            return True

        if self._has_cooling() and temperature < self._setpoints[C0]:
            return True

        return False

    def _has_full_config(self):
        return self._has_heating() and self._has_cooling()

    def _has_heating(self):
        return self._setpoints[H1] is not None and self._setpoints[H0] is not None

    def _has_cooling(self):
        return self._setpoints[C0] is not None and self._setpoints[C1] is not None
