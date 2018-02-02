#!/usr/bin/env python
"""
Script to handle the Heat Pump at 40 Stokes Valley Road, AWS IoT connected.

V1 board:
    Input Pins:
        Pin 4:  Photo Transistor
        Pin 22: DHT22
    Output Pins:
        Pin 18: DHT22 On/Off
        Pin 23: IR LED

V2 board:
    Input Pins:
        Pin 4:  Photo Transistor
        Pin 22: DHT22
        Pin 24: LED Monitor Output
    Output Pins:
        Pin 17: LED Monitor Input On/Off*
        Pin 18: DHT22 On/Off - Active High
        Pin 23: IR LED - Active High
        Pin 25: LED Monitor Output On/Off - Active Low

        *This is actually connected to the D0 pin on the 74HC373N (Pin 3).
        The cathode of the LEDs are connected to the LE Pin on the 74H373N
        (Pin 11), which is Active High.
"""
import logging
import time
from copy import deepcopy

try:
    import Adafruit_DHT
    from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException
except ImportError:
    if __name__ == '_main__':
        raise

import heatpump
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

_FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_STREAM_HANDLER = logging.StreamHandler()
_STREAM_HANDLER.setFormatter(_FORMATTER)

logger = logging.getLogger(__name__) # pylint: disable=invalid-name
logger.addHandler(_STREAM_HANDLER)


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
        logger.debug(state)
        if not state:
            logger.debug('not state, bye')
            return

        try:
            heatpump_command = self.heatpump.get_action(state['temperature'])
        except KeyError:
            logger.debug('key error')
            return

        if not heatpump_command:
            logger.debug('no command')
            return

        logger.debug('might be telling heatpump to %r', heatpump_command)

        if heatpump_command == self.heatpump.current_action:
            logger.debug('not telling heatpump to %r', heatpump_command)
            return

        function = heatpump_command['action']
        logger.debug('Sending command to heatpump: %s', function)
        try:
            self.heatpump.send_command(heatpump_command)
        except IOError:
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

    def send_set_points(self):
        """Send set points to IoT"""
        message = {
            'state': {
                'reported': self.heatpump.setpoints
            }
        }
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

    @property
    def environment(self):
        """Obtains a sample from the sensor"""
        return self.sensor.sample

    def compute_state_difference(self, new_state):
        """Computes the difference between the current state and the new state"""
        if not self.temperature and not self.humidity:
            return new_state

        new_state = deepcopy(new_state)

        if self.temperature:
            try:
                if abs(self.temperature - new_state['temperature']) < 0.2:
                    del new_state['temperature']
            except KeyError:
                pass

        if self.humidity:
            try:
                if abs(self.humidity - new_state['humidity']) < 0.2:
                    del new_state['humidity']
            except KeyError:
                pass

        return new_state

    def send_sample(self, environment):
        """Send state to IoT"""
        new_state = {'temperature': environment.temperature,
                     'humidity': environment.humidity}
        reported_state = self.compute_state_difference(new_state)

        try:
            self.temperature = reported_state['temperature']
        except KeyError:
            pass

        try:
            self.humidity = reported_state['humidity']
        except KeyError:
            pass

        now = time.time()
        logger.debug('last_update: %s, now: %s, t: %s, h: %s',
                     str(self.last_update),
                     str(now),
                     str(environment.temperature),
                     str(environment.humidity))

        if not reported_state:
            return None

        self.last_update = now
        message = {'state': {'reported': reported_state}}
        logger.debug(message)
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

        return reported_state

def main():
    """Program entrypoint"""
    heatpump = Heatpump()
    heatpump.setpoints = DEFAULT_SETPOINTS

    sensor = Sensor(SENSOR, DHT_PIN, DHT_ONOFF_PIN)

    credentials = Credentials(root_ca_path=ROOT_CA_PATH,
                              private_key_path=PRIVATE_KEY_PATH,
                              certificate_path=CERTIFICATE_PATH)

    iot = iot = IoT(CLIENT_ID)
    iot.connect(HOST, credentials)

    controller = Controller()
    controller.heatpump = heatpump
    controller.sensor = sensor
    controller.iot = iot

    controller.subscribe()
    controller.send_set_points()
    while True:
        environment_state = controller.environment
        if environment_state:
            reported_state = controller.send_sample(environment_state)
            controller.process_state(reported_state)
        time.sleep(2)

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    awslogger = logging.getLogger("AWSIoTPythonSDK") # pylint: disable=invalid-name
    awslogger.setLevel(logging.WARNING)
    awslogger.addHandler(_STREAM_HANDLER)

    heatpump.logger.setLevel(logging.DEBUG)
    heatpump.logger.addHandler(_STREAM_HANDLER)

    main()
