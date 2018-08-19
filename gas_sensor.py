#!/usr/bin/env python
"""
Script to publish the temperature of the thermocouple attached to the gas heater
at 40 Stokes Valley Road to AWS IoT
"""
import logging
import time

from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException

from mcp9000 import  MCP9000
from iot import IoT, Credentials, DataItem, TemperatureSensor
from iot import topics, setup_aws_logging
from iot import STREAM_HANDLER, HOST, ROOT_CA_PATH

CERTIFICATE_PATH = '../40stokesMCP.cert.pem'
PRIVATE_KEY_PATH = '../40stokesMCP.private.key'
CLIENT_ID = '40stokesMCP'

MCP9000_BUS = 1
MCP9000_ADDRESS = 0x63

TOPICS = topics('$aws/things/40stokesMCP/shadow/update')

logger = logging.getLogger(__name__) # pylint: disable=invalid-name
logger.addHandler(STREAM_HANDLER)

class Thing(TemperatureSensor): # pylint: disable=too-few-public-methods
    """Thing class"""
    def __init__(self, temperature=None):
        TemperatureSensor.__init__(self, temperature)
        self.mcp9000 = None
        self.iot = None

    def _set_temperature(self, temperature):
        if not self.temperature:
            self._temperature = DataItem(temperature)
            self._send_sample()
        elif self.temperature.value != temperature:
            self.temperature.value = temperature
            self._send_sample()
        else:
            if time.time() - self.temperature.last_update > 60:
                print('')
                self._send_sample()

    def _send_sample(self):
        """
        Sends state update to IoT
        """
        message = {'state': {'reported': {'temperature': self.temperature.value}}}
        logger.debug(message)
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout')

def _setup_logging():
    logger.setLevel(logging.DEBUG)

    setup_aws_logging(STREAM_HANDLER)

    gas_logger = logging.getLogger('gas')
    gas_logger.setLevel(logging.DEBUG)
    gas_logger.addHandler(STREAM_HANDLER)

def _main():
    _setup_logging()

    mcp9000 = MCP9000(MCP9000_BUS, MCP9000_ADDRESS)

    credentials = Credentials(root_ca_path=ROOT_CA_PATH,
                              private_key_path=PRIVATE_KEY_PATH,
                              certificate_path=CERTIFICATE_PATH)

    iot = IoT(CLIENT_ID)
    iot.connect(HOST, credentials)


    thing = Thing()
    thing.mcp9000 = mcp9000
    thing.iot = iot

    while True:
        thing.temperature = mcp9000.temperature
        time.sleep(2)

if __name__ == '__main__':
    _main()
