#!/usr/bin/env python
"""Script to handle the Heat Pump at 40 Stokes Valley Road, AWS IoT connected."""
import logging
import time
import json

import Adafruit_DHT
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException
from sensor import Sensor
from heatpump import Heatpump

HOST = 'a1pxxd60vwqsll.iot.ap-southeast-2.amazonaws.com'
ROOT_CA_PATH = '../root-CA.crt'
CERTIFICATE_PATH = '../40stokesDHT.cert.pem'
PRIVATE_KEY_PATH = '../40stokesDHT.private.key'
CLIENT_ID = '40stokesDHT'
SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 22
DHT_ONOFF_PIN = 18

TOPICS = {
    'shadow_update': '$aws/things/40stokesDHT/shadow/update',
    'shadow_update_accepted': '$aws/things/40stokesDHT/shadow/update/accepted',
    'shadow_update_rejected': '$aws/things/40stokesDHT/shadow/update/rejected',
    'update_state': '$aws/things/40stokesDHT/shadow/update/delta'
}

class IoT(object):
    """Main Class"""
    def __init__(self):
        self.humidity = None
        self.temperature = None
        self.function = None
        self.last_update = None
        self.last_heatpump_command = None


        self.mqtt_client = None

        self.sensor = Sensor(SENSOR, DHT_PIN, DHT_ONOFF_PIN)

        self.heatpump = Heatpump()
        self.heatpump.set_setpoints({'heating_start': 16,
                                     'heating_stop': 18,
                                     'cooling_stop': 22,
                                     'cooling_start': 24})

    def connect(self):
        """Connect to the IoT service"""
        logger.debug('connecting...')
        mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
        mqtt_client.configureEndpoint(HOST, 8883)
        mqtt_client.configureCredentials(ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)

        # AWSIoTMQTTClient connection configuration
        mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
        mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
        mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec

        mqtt_client.connect()
        self.mqtt_client = mqtt_client

    def subscribe(self):
        """Set up MQTT subscriptions"""
        logger.debug('subscribing...')
        self.mqtt_client.subscribe(
            TOPICS['shadow_update_accepted'],
            1,
            self.shadow_update_accepted_callback)
        self.mqtt_client.subscribe(
            TOPICS['shadow_update_rejected'],
            1,
            self.shadow_update_rejected_callback)
        self.mqtt_client.subscribe(
            TOPICS['update_state'],
            1,
            self.update_state_callback)

    def shadow_update_accepted_callback(self, client, userdata, message):
        """State update accepted callback function"""
        pass

    def shadow_update_rejected_callback(self, _client, _userdata, _message):
        """State update rejected callback function"""
        logger.warning("State update rejected")
        self.humidity = None
        self.temperature = None
        self.function = None

    def update_state_callback(self, _client, _userdata, message):
        """Callback to process a desired state change"""
        logger.debug("Received new desired state:")
        logger.debug(message.payload)

        parsed = json.loads(message.payload)

        try:
            desired_state = parsed['state']
        except KeyError as error:
            logger.warning('key error: %s', str(error))
            return

        logger.debug("desired state: %s", json.dumps(desired_state))

        self.heatpump.set_setpoints(desired_state)
        reported_state = self.heatpump.get_setpoints()

        # send state update
        message = {'state': {'reported': reported_state}}
        raw_message = json.dumps(message)
        logger.debug("reported state: %s", raw_message)
        try:
            self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

    def process_state(self, state):
        """Determine what action (if any) to take based on the most recent state change"""
        try:
            heatpump_command = self.heatpump.get_action(state['temperature'])
            if heatpump_command is None:
                return

            function = heatpump_command['action']
            logger.debug('Sending command to heatpump: %s', function)
            if self.heatpump.send_command(heatpump_command) != 0:
                logger.warning('could not send command to heat pump')
                return

            self.function = function
            reported_state = {'function': self.function}
            message = {'state': {'reported': reported_state}}
            raw_message = json.dumps(message)
            try:
                self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
            except publishTimeoutException:
                logger.warning('publish timeout, clearing local state')
                self.humidity = None
                self.temperature = None

        except KeyError:
            pass

    def send_set_points(self):
        """Send set points to IoT"""
        message = {
            'state': {
                'reported': self.heatpump.get_setpoints()
            }
        }
        raw_message = json.dumps(message)
        try:
            self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

    def send_sample(self):
        """Send state to IoT"""
        humidity, temperature = self.sensor.read()

        reported_state = {}
        now = time.time()
        forced_update = self.last_update is None or now > self.last_update + 60
        logger.debug('last_update: %s, now: %s, force update: %s, t: %s, h: %s',
                     str(self.last_update),
                     str(now),
                     str(self.last_update is None or now > self.last_update + 60),
                     str(temperature),
                     str(humidity))
        if humidity is not None:
            if forced_update or self.humidity is None or abs(humidity - self.humidity) > 0.2:
                self.humidity = humidity
                reported_state['humidity'] = humidity
        else:
            logger.debug('no humidity')

        if temperature is not None:
            if forced_update or self.temperature is None or abs(temperature - self.temperature) > 0.2:
                self.temperature = temperature
                reported_state['temperature'] = temperature
        else:
            logger.debug('no temperature')

        if reported_state == {}:
            return None

        self.last_update = now
        message = {'state': {'reported': reported_state}}
        raw_message = json.dumps(message)
        logger.debug(raw_message)
        try:
            self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

        return reported_state

def main():
    """Program entrypoint"""
    iot = IoT()
    iot.connect()
    iot.subscribe()
    iot.send_set_points()
    while True:
        state = iot.send_sample()
        if state is not None:
            iot.process_state(state)
        time.sleep(2)

if __name__ == '__main__':
    FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setFormatter(FORMATTER)
    logger = logging.getLogger("AWSIoTPythonSDK") # pylint: disable=invalid-name
    logger.setLevel(logging.WARNING)
    logger.addHandler(STREAM_HANDLER)

    logger = logging.getLogger("40stokesDHT") # pylint: disable=invalid-name
    logger.setLevel(logging.DEBUG)
    logger.addHandler(STREAM_HANDLER)
    main()
