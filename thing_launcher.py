#!/usr/bin/env python
"""Launcher"""
import importlib
import os
import re
import logging
import yaml
import boto3
import watchtower

import iot

def configure_logging(logging_config):
    """Configure logging"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    watchtower_config = {
        'use_queues': True,
        'send_interval': 10,
        'max_batch_size': 1048576,
        'max_batch_count': 20,
    }

    for module in logging_config:
        config = logging_config[module]

        logger = logging.getLogger(module)
        logger.setLevel(logging.__dict__[config['level']])
        logger.addHandler(stream_handler)

        try:
            session = boto3.session.Session(profile_name=config['aws_profile'])
            watchtower_config['log_group'] = config['log_group']
            watchtower_config['boto3_session'] = session

            cwlogs_handler = watchtower.CloudWatchLogHandler(**watchtower_config)
            logger.addHandler(cwlogs_handler)
        except KeyError:
            pass

if __name__ == "__main__":
    MODULE_NAME = os.path.basename(__file__).replace('.pyc?', '')
    MODULE = importlib.import_module(MODULE_NAME)

    with open('config.yaml', 'r') as stream:
        CONFIG = yaml.load(stream)

    configure_logging(CONFIG['logging'])

    MODULE_CONFIG = CONFIG[MODULE_NAME]
    IOT_CONFIG = MODULE_CONFIG['aws_iot']

    CREDENTIALS = iot.Credentials(root_ca_path=IOT_CONFIG['root_ca_path'],
                                  private_key_path=IOT_CONFIG['private_key_path'],
                                  certificate_path=IOT_CONFIG['certificate_path'])

    IOT = iot.IoT(IOT_CONFIG['client_id'])
    IOT.connect(IOT_CONFIG['endpoint'], CREDENTIALS)

    CONTROLLER_CLASS = re.sub(r'(^|_)(.)', lambda x: x.group(2).upper(), MODULE_NAME)
    CONTROLLER = MODULE.__dict__[CONTROLLER_CLASS](MODULE_CONFIG)
    CONTROLLER.iot = IOT
    CONTROLLER.start()
