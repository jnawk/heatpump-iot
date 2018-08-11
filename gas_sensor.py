#!/usr/bin/env python
"""
Script to publish the temperature of the thermocouple attached to the gas heater
at 40 Stokes Valley Road to AWS IoT
"""
import logging
import time

from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException

from mcp9000 import  MCP9000
from iot import IoT, Credentials, topics, setup_aws_logging

HOST = 'a1pxxd60vwqsll.iot.ap-southeast-2.amazonaws.com'
ROOT_CA_PATH = '../root-CA.crt'
CERTIFICATE_PATH = '../40stokesMCP.cert.pem'
PRIVATE_KEY_PATH = '../40stokesMCP.private.key'
CLIENT_ID = '40stokesMCP'

MCP9000_BUS = 1
MCP9000_ADDRESS = 0x63

TOPICS = topics('$aws/things/40stokesMCP/shadow/update')

_FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_STREAM_HANDLER = logging.StreamHandler()
_STREAM_HANDLER.setFormatter(_FORMATTER)

logger = logging.getLogger(__name__) # pylint: disable=invalid-name
logger.addHandler(_STREAM_HANDLER)

class Thing(object):
    """Thing class"""
    def __init__(self):
        self.mcp9000 = None
        self.iot = None

    def send_sample(self, temperature):
        """
        Sends state update to IoT
        """
        message = {'state': {'reported': {'temperature': temperature}}}
        logger.debug(message)
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout')

def _setup_logging():
    logger.setLevel(logging.DEBUG)

    setup_aws_logging(_STREAM_HANDLER)

    gas_logger = logging.getLogger('gas')
    gas_logger.setLevel(logging.DEBUG)
    gas_logger.addHandler(_STREAM_HANDLER)

def _main():
    _setup_logging()

    mcp9000 = MCP9000(MCP9000_BUS, MCP9000_ADDRESS)

    credentials = Credentials(root_ca_path=ROOT_CA_PATH,
                              private_key_path=PRIVATE_KEY_PATH,
                              certificate_path=CERTIFICATE_PATH)

    iot = iot = IoT(CLIENT_ID)
    iot.connect(HOST, credentials)


    thing = Thing()
    thing.mcp9000 = mcp9000
    thing.iot = iot

    while True:
        thing.send_sample(mcp9000.temperature)
        time.sleep(2)

if __name__ == '__main__':
    _main()
