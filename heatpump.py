"""Heatpump module"""
import subprocess
import logging

_A = 'action'
_C = 'command'
_T = 'trend'

START_COOLING = {_A: 'cooling', _C: 'maxcold', _T: 1}
SHUTDOWN = {_A: 'shutdown', _C: 'stokesoff', _T: 0}
START_HEATING = {_A: 'heating', _C: 'stokesheat', _T: -1}

H1 = 'heating_start'
H0 = 'heating_stop'
C0 = 'cooling_stop'
C1 = 'cooling_start'

_NEEDS_SET = '%s needs to be set'
_BACKWARDS = '%s needs to be less than %s'

logger = logging.getLogger(__name__) # pylint: disable=invalid-name

class Heatpump(object):
    """Heatpump class"""
    def __init__(self):
        self._setpoints = {H1: None,
                           H0: None,
                           C0: None,
                           C1: None}
        self._current_action = None
        self.led_verify = None
        self._heater = None

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

    @property
    def heater(self):
        """The gas_sensor"""
        return self._heater

    @heater.setter
    def heater(self, heater):
        """Sets the gas_sensor"""
        self._heater = heater

    def get_action(self, temperature):
        """Computes the action to take based on the current temperature"""
        if self._is_hot(temperature):
            if self._heater_on():
                logger.debug('heater is on, not cooling')
            else:
                return START_COOLING

        if self._is_cold(temperature):
            return START_HEATING

        if self._is_shutdown(temperature):
            return SHUTDOWN

        return None

    def send_command(self, command):
        """sends a command to the heatpump"""
        self.led_verify.reset()
        if subprocess.call(["irsend", "SEND_ONCE", "heat_pump", command[_C]]) == 0:
            if self.led_verify.state:
                self._current_action = command
                return command

        raise IOError()

    def _is_hot(self, temperature):
        logger.debug('%s > %s: is_hot: %r',
                     temperature,
                     self._setpoints[C1],
                     temperature > self._setpoints[C1])
        return self._has_cooling() and temperature > self._setpoints[C1]

    def _is_cold(self, temperature):
        logger.debug('%s < %s: is_cold: %r',
                     temperature,
                     self._setpoints[H1],
                     temperature < self._setpoints[H1])
        return self._has_heating() and temperature < self._setpoints[H1]

    def _is_shutdown(self, temperature):
        if self._has_full_config():
            logger.debug('%s < %s < %s: is_shutdown: %r',
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

    def _heater_on(self):
        if self.heater is not None:
            return self.heater.heater_is_on

        return False

    def _has_full_config(self):
        return self._has_heating() and self._has_cooling()

    def _has_heating(self):
        return self._setpoints[H1] and self._setpoints[H0]

    def _has_cooling(self):
        return self._setpoints[C0] and self._setpoints[C1]
