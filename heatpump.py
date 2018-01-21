"""Heatpump module"""
import subprocess

_A = 'action'
_C = 'command'

START_COOLING = {_A: 'cooling', _C: 'maxcold'}
SHUTDOWN = {_A: 'shutdown', _C: 'stokesoff'}
START_HEATING = {_A: 'heating', _C: 'stokesheat'}

_H1 = 'heating_start'
_H0 = 'heating_stop'
_C0 = 'cooling_stop'
_C1 = 'cooling_start'

_NEEDS_SET = '%s needs to be set'
_BACKWARDS = '%s needs to be less than %s'

class Heatpump(object):
    """Heatpump class"""
    def __init__(self):
        self.state = {_H1: None,
                      _H0: None,
                      _C0: None,
                      _C1: None}

    def set_setpoints(self, setpoints):
        """Updates the setpoints"""
        target = {_H1: setpoints[_H1] if setpoints.has_key(_H1) else self.state[_H1],
                  _H0: setpoints[_H0] if setpoints.has_key(_H0) else self.state[_H0],
                  _C0: setpoints[_C0] if setpoints.has_key(_C0) else self.state[_C0],
                  _C1: setpoints[_C1] if setpoints.has_key(_C1) else self.state[_C1]}

        if target[_H1] is None:
            raise ValueError(_NEEDS_SET % _H1)

        if target[_H0] is None:
            raise ValueError(_NEEDS_SET % _H0)

        if target[_H1] >= target[_H0]:
            raise ValueError(_BACKWARDS % (_H1, _H0))

        if target[_C0] is None:
            raise ValueError(_NEEDS_SET % _C0)

        if target[_C1] is None:
            raise ValueError(_NEEDS_SET % _C1)

        if target[_C0] >= target[_C1]:
            raise ValueError(_BACKWARDS % (_C0, _C1))

        if target[_H0] >= target[_C0]:
            raise ValueError(_BACKWARDS % (_H0, _C0))

        self.state = target

    def get_setpoints(self):
        """Returns the setpoints"""
        return self.state

    def get_action(self, temperature):
        """Computes the action to take based on the current temperature"""
        if self._is_hot(temperature):
            return START_COOLING

        elif self._is_cold(temperature):
            return START_HEATING

        elif self._is_goldielocks(temperature):
            return SHUTDOWN

        elif self._has_heating() and self._has_cooling():
            return None

        # if we succeed either of these next two, then we have partial configuration
        elif self._has_heating() and temperature > self.state[_H0]:
            return SHUTDOWN

        elif self._has_cooling() and temperature < self.state[_C0]:
            return SHUTDOWN

        return None

    @staticmethod
    def send_command(command):
        """sends a command to the heatpump"""
        return subprocess.call(["irsend", "SEND_ONCE", "heat_pump", command[_C]])

    def _is_hot(self, temperature):
        return self._has_cooling() and temperature > self.state[_C1]

    def _is_cold(self, temperature):
        return self._has_heating() and temperature < self.state[_H1]

    def _is_goldielocks(self, temperature):
        if not self._has_heating() and not self._has_cooling():
            # if we don't have both heating and cooling configuration, we can't
            # possibly know if we are neither too hot nor too cold!
            return False

        return temperature > self.state[_H0] and temperature < self.state[_C0]

    def _has_heating(self):
        return self.state[_H1] is not None and self.state[_H0] is not None

    def _has_cooling(self):
        return self.state[_C0] is not None and self.state[_C1] is not None
