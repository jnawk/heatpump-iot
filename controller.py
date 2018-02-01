#!/usr/bin/env python
"""Script to handle the Heat Pump at 40 Stokes Valley Road, AWS IoT connected."""
import logging
import time
from copy import deepcopy

try:
    import Adafruit_DHT
    from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException
except ImportError:
    if __name__ == '_main__':
        raise

from heatpump import Heatpump, H1, H0, C0, C1

try:
    from sensor import Sensor
    from iot import IoT, Credentials
except ImportError:
    if __name__ == '_main__':
        raise

try:
    SENSOR = Adafruit_DHT.DHT22
except NameError:
    if __name__ == '_main__':
        raise

HOST = 'a1pxxd60vwqsll.iot.ap-southeast-2.amazonaws.com'
ROOT_CA_PATH = '../root-CA.crt'
CERTIFICATE_PATH = '../40stokesDHT.cert.pem'
PRIVATE_KEY_PATH = '../40stokesDHT.private.key'
CLIENT_ID = '40stokesDHT'
DHT_PIN = 22
DHT_ONOFF_PIN = 18

DEFAULT_SETPOINTS = {H1: 16, H0: 18, C0: 22, C1: 24}

SHADOW_UPDATE_TOPIC = '$aws/things/40stokesDHT/shadow/update'

TOPICS = {
    'shadow_update': SHADOW_UPDATE_TOPIC,
    'shadow_update_accepted': '%s/%s' % (SHADOW_UPDATE_TOPIC, 'accepted'),
    'shadow_update_rejected': '%s/%s' % (SHADOW_UPDATE_TOPIC, 'rejected'),
    'update_state': '%s/%s' % (SHADOW_UPDATE_TOPIC, 'delta')
}

class Controller(object):
    """Main Class"""
    def __init__(self):
        self.humidity = None
        self.temperature = None
        self.function = None
        self.last_update = None
        self.last_heatpump_command = None
        self.sensor = None
        self.heatpump = None
        self.iot = None

    def subscribe(self):
        """Set up MQTT subscriptions"""
        logger.debug('subscribing...')
        self.iot.subscribe(
            TOPICS['shadow_update_rejected'],
            self.shadow_update_rejected_callback)
        self.iot.subscribe(
            TOPICS['update_state'],
            self.update_state_callback)

    def shadow_update_rejected_callback(self, _client, _userdata, _message):
        """State update rejected callback function"""
        logger.warning("State update rejected")
        self.humidity = None
        self.temperature = None
        self.function = None

    def update_state_callback(self, _client, _userdata, message):
        """Callback to process a desired state change"""
        logger.debug("Received new desired state:")
        logger.debug(message)

        try:
            desired_state = message['state']
        except KeyError as error:
            logger.warning('key error: %s', str(error))
            return

        logger.debug("desired state: %s", desired_state)

        self.heatpump.setpoints = desired_state
        reported_state = self.heatpump.setpoints

        # send state update
        message = {'state': {'reported': reported_state}}
        logger.debug("reported state: %s", message)
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
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
            try:
                self.iot.publish(TOPICS['shadow_update'], message)
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
            self.iot.publish(TOPICS['shadow_update'], message)
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
            self.iot.publish(TOPICS['shadow_update'], message)
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
