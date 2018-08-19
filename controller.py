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
        Pin 24: 47HC373N Q0
    Output Pins:
        Pin 17: 74HC373N D0
        Pin 18: 74HC4066 1C - DHT22 VCC
        Pin 23: 74HC4066 3C - IR LEDs VCC
        Pin 25: 74HC4066 4C - 74HC373N LE

    When running the LED, drive pin 17 high and pin 25 low. The LEDs cathodes are
    connected to the LE pin on the 74HC4066.

"""
import logging
import time
from copy import deepcopy

from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException
from heatpump import Heatpump, H1, H0, C0, C1

from gpio import DHT22, LEDVerify
from iot import IoT, Credentials, DataItem, TemperatureSensor
from iot import topics, setup_aws_logging
from iot import STREAM_HANDLER, HOST, ROOT_CA_PATH

CERTIFICATE_PATH = '../40stokesDHT.cert.pem'
PRIVATE_KEY_PATH = '../40stokesDHT.private.key'
CLIENT_ID = '40stokesDHT'

DHT_PIN = 22
DHT_ONOFF_PIN = 18

LV_LE_PIN = 25
LV_D0_PIN = 17
LV_Q0_PIN = 24

DEFAULT_SETPOINTS = {H1: 16, H0: 18, C0: 22, C1: 24}

TOPICS = topics('$aws/things/40stokesDHT/shadow/update')

logger = logging.getLogger(__name__) # pylint: disable=invalid-name
logger.addHandler(STREAM_HANDLER)

class Controller(object):
    """Main Class"""
    def __init__(self):
        self.dht22 = None
        self.heatpump = None
        self.iot = None
        self._state = State()

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
        self.state.reset()

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
            self.state.reset()

    def process_state(self, new_state):
        """
        Determines the action to take based on the new_state, and takes it.
        """
        logger.debug('current state: %r', self.state)
        logger.debug('new state: %r', new_state)
        if not new_state:
            raise ValueError('please give a state')

        heatpump_command = self.heatpump.get_action(new_state.temperature)

        if not heatpump_command:
            logger.debug('nothing to do')
            return

        logger.debug('might be telling heatpump to %r', heatpump_command)

        if heatpump_command == self.heatpump.current_action:
            # command for this temperature is what we're already doing
            if self.state.temperature:
                if self.state.temperature.is_noise(new_state.temperature):
                    logger.debug('noise')
                    return
                trend = self.state.temperature.compute_trend(new_state.temperature)
                if trend and trend == heatpump_command['trend']:
                    logger.debug('we should tell it to do it again')
                else:
                    logger.debug('not telling heatpump to %r', heatpump_command)
                    return

        function = heatpump_command['action']
        logger.debug('Sending command to heatpump: %s', function)
        try:
            self.heatpump.send_command(heatpump_command)
        except IOError:
            logger.warning('could not send command to heat pump')
            return

        self.state.function = function
        reported_state = {'function': function}
        message = {'state': {'reported': reported_state}}
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.state.reset()

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
            self.state.reset()

    @property
    def state(self):
        """Current state"""
        return self._state

    @property
    def environment(self):
        """Obtains a sample from the sensor"""
        sample = self.dht22.sample
        logger.debug('sample: %r', sample)
        return sample

    def compute_state_difference(self, new_state):
        """Computes the difference between the current state and the new state"""
        if not self.state.temperature and not self.state.humidity:
            return new_state

        new_state = deepcopy(new_state)
        if self.state.temperature:
            try:
                if abs(self.state.temperature.value - new_state['temperature']) < 0.2:
                    del new_state['temperature']
            except KeyError:
                pass

        if self.state.humidity:
            try:
                if abs(self.state.humidity.value - new_state['humidity']) < 0.2:
                    del new_state['humidity']
            except KeyError:
                pass

        return new_state

    def send_sample(self, environment):
        """
        Determines the difference in the environment state and sends those
        differences to IoT.  Also updates current state.
        """
        new_state = {'temperature': environment.temperature,
                     'humidity': environment.humidity}

        now = time.time()
        different_state = self.compute_state_difference(new_state)
        if not self.state.last_update or self.state.last_update + 60 < now:
            reported_state = new_state
        else:
            reported_state = different_state

        try:
            self.state.temperature = reported_state['temperature']
        except KeyError:
            pass

        try:
            self.state.humidity = reported_state['humidity']
        except KeyError:
            pass

        logger.debug('last_update: %s, now: %s, t: %s, h: %s',
                     str(now),
                     str(self.state.last_update),
                     str(environment.temperature),
                     str(environment.humidity))

        if not reported_state:
            return None

        message = {'state': {'reported': reported_state}}
        logger.debug(message)
        try:
            self.iot.publish(TOPICS['shadow_update'], message)
        except publishTimeoutException:
            logger.warning('publish timeout, clearing local state')
            self.state.reset()

        return reported_state

class State(TemperatureSensor):
    """Holds the current state"""
    def __init__(self, humidity=None, temperature=None, function=None):
        """Constructor"""
        TemperatureSensor.__init__(self, temperature)

        self._humidity = humidity
        self._function = function

    def reset(self):
        """Clears out the temperature, humidity and function properties"""
        self._temperature = None
        self._humidity = None
        self._function = None

    @property
    def humidity(self):
        """The humidity DataItem"""
        return self._humidity

    @humidity.setter
    def humidity(self, humidity):
        if not humidity:
            raise ValueError('humidity is required')
        if not self._humidity:
            self._humidity = DataItem(humidity)
        else:
            self._humidity.value = humidity

    def _set_temperature(self, temperature):
        if not temperature:
            raise ValueError('temperature is required')
        if not self._temperature:
            self._temperature = DataItem(temperature)
        else:
            self._temperature.value = temperature

    @property
    def function(self):
        """What the heatpump is supposed to be doing"""
        return self._function

    @function.setter
    def function(self, function):
        self._function = function

    @property
    def last_update(self):
        """
        The earliest last-update time.

        If neither temperature or humidity have been updated, then this will return
        None.

        If only one of temperature or humidity have been updated, then this will
        return the time of the most recent update.

        If both temperature and humidity have been updated, then this will return
        the earlier of the most recent update of temperature or most recent update
        of humidity.
        """
        if self.humidity and self._temperature:
            return min(self._humidity.last_update, self._temperature.last_update)

        if self._temperature:
            return self._temperature.last_update

        if self._humidity:
            return self._humidity.last_update

        return None

    def __repr__(self):
        pattern = '%s(humidity=%r, temperature=%r, function=%r)'
        return pattern % (self.__class__.__name__,
                          self.humidity,
                          self.temperature,
                          self.function)

def _setup_logging():
    logger.setLevel(logging.DEBUG)

    setup_aws_logging(STREAM_HANDLER)

    heatpump_logger = logging.getLogger('heatpump')
    heatpump_logger.setLevel(logging.DEBUG)
    heatpump_logger.addHandler(STREAM_HANDLER)

def _main():
    _setup_logging()

    dht22 = DHT22(DHT_PIN, DHT_ONOFF_PIN)
    led_verify = LEDVerify(LV_LE_PIN, LV_D0_PIN, LV_Q0_PIN)

    heatpump = Heatpump()
    heatpump.setpoints = DEFAULT_SETPOINTS
    heatpump.led_verify = led_verify

    credentials = Credentials(root_ca_path=ROOT_CA_PATH,
                              private_key_path=PRIVATE_KEY_PATH,
                              certificate_path=CERTIFICATE_PATH)

    iot = IoT(CLIENT_ID)
    iot.connect(HOST, credentials)

    controller = Controller()
    controller.heatpump = heatpump
    controller.dht22 = dht22
    controller.iot = iot

    controller.subscribe()
    controller.send_set_points()
    while True:
        environment_state = controller.environment
        current_state = controller.state
        if environment_state and current_state:
            if environment_state.temperature and environment_state.humidity:
                controller.process_state(environment_state)
                controller.send_sample(environment_state)
        time.sleep(2)

if __name__ == '__main__':
    _main()
