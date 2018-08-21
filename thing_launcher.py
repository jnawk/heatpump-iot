#!/usr/bin/env python
"""Launcher"""
from __future__ import print_function
import importlib
import os
import re
import logging
import yaml

from iot import IoT, Credentials

def setup_aws_logging(stream_handler):
    """Configures AWS Logging"""
    aws_logger = logging.getLogger('AWSIoTPythonSDK')
    aws_logger.setLevel(logging.WARNING)
    aws_logger.addHandler(stream_handler)

if __name__ == "__main__":
    FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setFormatter(FORMATTER)

    setup_aws_logging(STREAM_HANDLER)

    MODULE_NAME = os.path.basename(__file__).replace('.pyc?', '')
    MODULE = importlib.import_module(MODULE_NAME)

    MODULE.logger.addHandler(STREAM_HANDLER)

    with open('config.yaml', 'r') as stream:
        CONFIG = yaml.load(stream)

    MODULE_CONFIG = CONFIG[MODULE_NAME]
    IOT_CONFIG = MODULE_CONFIG['aws_iot']

    CREDENTIALS = Credentials(root_ca_path=IOT_CONFIG['root_ca_path'],
                              private_key_path=IOT_CONFIG['private_key_path'],
                              certificate_path=IOT_CONFIG['certificate_path'])

    IOT = IoT(IOT_CONFIG['client_id'])
    IOT.connect(IOT_CONFIG['endpoint'], CREDENTIALS)

    CONTROLLER_CLASS = re.sub(r'(^|_)(.)', lambda x: x.group(2).upper(), MODULE_NAME)
    CONTROLLER = MODULE.__dict__[CONTROLLER_CLASS](MODULE_CONFIG)
    CONTROLLER.iot = IOT
    CONTROLLER.start()
