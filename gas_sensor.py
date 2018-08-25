#!/usr/bin/env python
"""
Script to publish the temperature of the thermocouple attached to the gas heater
at 40 Stokes Valley Road to AWS IoT
"""
import logging
import time

from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException

try:
    import mcp9000
except ImportError:
    pass
import iot

logger = logging.getLogger(__name__) # pylint: disable=invalid-name

class GasSensor(iot.TemperatureSensor):
    """Gas Sensor Controller Class"""
    def __init__(self, config):
        super(GasSensor, self).__init__()
        self.iot = None

        try:
            logger.setLevel(logging.__dict__[config['log_level']])
            mcp9000_config = config['mcp9000']
            self.mcp9000 = mcp9000.MCP9000(mcp9000_config['bus'], mcp9000_config['address'])
        except KeyError:
            self.threshold = config['threshold']
            self.client_id = config['client_id']

    def start(self):
        """Start the controller"""
        while True:
            self.temperature = self.mcp9000.temperature
            time.sleep(2)

    @property
    def heater_is_on(self):
        """True if the heater is on"""
        try:
            return self.temperature.value > self.threshold
        except TypeError:
            return False

    @property
    def topics(self):
        """MQTT Topics for this thing"""
        return iot.topics(self.client_id)

    def _set_temperature(self, temperature):
        if not self.temperature:
            self._temperature = iot.DataItem(temperature)
            self._send_sample()
        elif self.temperature.value != temperature:
            self.temperature.value = temperature
            self._send_sample()
        else:
            if time.time() - self.temperature.last_update > 60:
                self.temperature.value = temperature
                self._send_sample()

    def _send_sample(self):
        """
        Sends state update to IoT
        """
        message = {'state': {'reported': {'temperature': self.temperature.value}}}
        logger.debug(message)
        try:
            self.iot.publish(self.iot.topics['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout')
        except TypeError:
            pass
