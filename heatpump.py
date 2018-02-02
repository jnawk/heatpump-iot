"""Heatpump module"""
import subprocess
import logging

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

logger = logging.getLogger(__name__)

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
    def current_action(self):
        """Returns what the heatpump is supposed to be doing currently"""
        return self._current_action

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

    def send_command(self, command):
        """sends a command to the heatpump"""
        if subprocess.call(["irsend", "SEND_ONCE", "heat_pump", command[_C]]) == 0:
            self._current_action = command
        else:
            raise IOError()

    def _is_hot(self, temperature):
        logger.debug('%d > %d: %r',
                     temperature,
                     self._setpoints[C1],
                     temperature > self._setpoints[C1])
        return self._has_cooling() and temperature > self._setpoints[C1]

    def _is_cold(self, temperature):
        logger.debug('%d < %d: %r',
                     temperature,
                     self._setpoints[H1],
                     temperature < self._setpoints[H1]
        return self._has_heating() and temperature < self._setpoints[H1]

    def _is_shutdown(self, temperature):
        if self._has_full_config():
            logger.debug('%d < %d < %d: %r',
                         self._setpoints[H0],
                         temperature,
                         self._setpoints[C0],
                         temperature > self._setpoints[H0] and temperature < self._setpoints[C0])
            return temperature > self._setpoints[H0] and temperature < self._setpoints[C0]

        if self._has_heating() and temperature > self._setpoints[H0]:
            return True

        if self._has_cooling() and temperature < self._setpoints[C0]:
            return True

        return False

    def _has_full_config(self):
        return self._has_heating() and self._has_cooling()

    def _has_heating(self):
        logger.debug('%s %s', bool(self._setpoints[H1]), bool(self.setpoints[H0]))
        return self._setpoints[H1] and self._setpoints[H0]

    def _has_cooling(self):
        logger.debug('%s %s', bool(self._setpoints[C0]), bool(self.setpoints[C1]))
        return self._setpoints[C0] and self._setpoints[C1]
