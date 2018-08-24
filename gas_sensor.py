#!/usr/bin/env python
"""
Script to publish the temperature of the thermocouple attached to the gas heater
at 40 Stokes Valley Road to AWS IoT
"""
import logging
import time

from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException

import mcp9000
import iot

# from mcp9000 import MCP9000
# from iot import DataItem, TemperatureSensor

logger = logging.getLogger(__name__) # pylint: disable=invalid-name

class GasSensor(iot.TemperatureSensor): # pylint: disable=too-few-public-methods
    """Gas Sensor Controller Class"""
    def __init__(self, config):
        super(GasSensor, self).__init__(self)
        logger.setLevel(logging.__dict__[config['log_level']])

        mcp9000_config = config['mcp9000']
        self.mcp9000 = mcp9000.MCP9000(mcp9000_config['bus'], mcp9000_config['address'])
        self.iot = None

    def start(self):
        """Start the controller"""
        while True:
            self.temperature = self.mcp9000.temperature
            time.sleep(2)

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
