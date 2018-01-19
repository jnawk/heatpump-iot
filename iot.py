#!/usr/bin/env python
"""Script to handle the Heat Pump at 40 Stokes Valley Road, AWS IoT connected."""
import logging
import time
import json
import subprocess
import numpy

import RPi.GPIO as GPIO
import Adafruit_DHT
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

HOST = 'a1pxxd60vwqsll.iot.ap-southeast-2.amazonaws.com'
ROOT_CA_PATH = '../root-CA.crt'
CERTIFICATE_PATH = '../40stokesDHT.cert.pem'
PRIVATE_KEY_PATH = '../40stokesDHT.private.key'
CLIENT_ID = '40stokesDHT'
SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 22
DHT_ONOFF_PIN = 18

LOGGER = None
MQTT_CLIENT = None

TOPICS = {
    'shadow_update': '$aws/things/40stokesDHT/shadow/update',
    'shadow_update_accepted': '$aws/things/40stokesDHT/shadow/update/accepted',
    'shadow_update_rejected': '$aws/things/40stokesDHT/shadow/update/rejected',
    'update_state': '$aws/things/40stokesDHT/shadow/update/delta'
}

class IoT:
    """Main Class"""
    def __init__(self):
        self.humidity = None
        self.temperature = None
        self.function = None
        self.last_update = None 
        self.last_heatpump_command = None

        # thresholds for heating / cooling, on / off
        self.cooling_start = 24 # if hotter than
        self.cooling_stop = 22  # once it is cooler than
        self.heating_start = 16 # if cooler than
        self.heating_stop = 18  # once it reaches

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger = logging.getLogger("AWSIoTPythonSDK")
        logger.setLevel(logging.WARNING)
        logger.addHandler(stream_handler)

        self.logger = logging.getLogger("40stokesDHT")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(stream_handler)

        self.mqtt_client = None

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DHT_ONOFF_PIN, GPIO.OUT)

    def connect(self):
        """Connect to the IoT service"""
        self.logger.debug('connecting...')
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
        self.logger.debug('subscribing...')
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

    def shadow_update_rejected_callback(self, client, userdata, message):
        """State update rejected callback function"""
        self.logger.warning("State update rejected")
        self.humidity = None
        self.temperature = None
        self.function = None

    def update_state_callback(self, client, userdata, message):
        """Callback to process a desired state change"""
        self.logger.debug("Received new desired state:")
        self.logger.debug(message.payload)

        parsed = json.loads(message.payload)

        try:
            desired_state = parsed['state']
        except KeyError as error:
            self.logger.warning('key error\n' + str(error))
            return

        target_state = {}

        self.logger.debug("desired state: " + json.dumps(desired_state))

        try:
            cooling_start = desired_state['cooling_start']
            target_state['cooling_start'] = cooling_start
        except KeyError as e:
            self.logger.debug("key error: " + str(e))
            cooling_start = None
            target_state['cooling_start'] = self.cooling_start

        try:
            cooling_stop = desired_state['cooling_stop']
            target_state['cooling_stop'] = cooling_stop
        except KeyError as e:
            self.logger.debug("key error: " + str(e))
            cooling_stop = None
            target_state['cooling_stop'] = self.cooling_stop

        try:
            heating_start = desired_state['heating_start']
            target_state['heating_start'] = heating_start
        except KeyError as e:
            self.logger.debug("key error: " + str(e))
            heating_start = None
            target_state['heating_start'] = self.heating_start

        try:
            heating_stop = desired_state['heating_stop']
            target_state['heating_stop'] = heating_stop
        except KeyError as e:
            self.logger.debug("key error: " + str(e))
            heating_stop = None
            target_state['heating_stop'] = self.heating_stop

        heating_valid = target_state['heating_start'] < target_state['heating_stop']
        cooling_valid = target_state['cooling_stop'] < target_state['cooling_start']
        heating_is_less_than_cooling = target_state['heating_stop'] < target_state['cooling_stop']

        if heating_valid and cooling_valid and heating_is_less_than_cooling:
            pass
        else:
            self.logger.warning('attempt to set invalid state')
            return

        self.logger.debug("target state: " + json.dumps(target_state))

        reported_state = {}

        if target_state['cooling_start'] is None or target_state['cooling_stop'] is None:
            self.logger.debug("incomplete or no cooling state")
            pass
        else:
            if cooling_start is not None and cooling_start != self.cooling_start:
                self.cooling_start = cooling_start
                reported_state['cooling_start'] = self.cooling_start

            if cooling_stop is not None and cooling_stop != self.cooling_stop:
                self.cooling_stop = cooling_stop
                reported_state['cooling_stop'] = self.cooling_stop

        if target_state['heating_start'] is None or target_state['heating_stop'] is None:
            self.logger.debug("incomplete or no heating state")
            pass
        else:
            if heating_start is not None and heating_start != self.heating_start:
                self.heating_start = heating_start
                reported_state['heating_start'] = self.heating_start

            if heating_start is not None and heating_stop != self.heating_stop:
                self.heating_stop = heating_stop
                reported_state['heating_stop'] = self.heating_stop

        # send state update
        message = {'state': {'reported': reported_state}}
        raw_message = json.dumps(message)
        self.logger.debug("reported state: " + raw_message)
        try:
            self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
        except Exception:
            self.logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

    def heatpump_command(self, function):
        """Send a command to the heatpump"""
        now = time.time()
        recent_update = self.last_heatpump_command is not None and self.last_heatpump_command + 60 > now
        if recent_update and function == self.function:
            # nothing to do
            return

        if function == 'cooling':
            command = 'maxcold'

        elif function == 'heating':
            command = 'stokesheat'

        elif function == 'shutdown':
            command = 'stokesoff'

        else:
            command = None

        if command is not None:
            self.last_heatpump_command = now
            self.logger.debug('Sending command to heatpump: ' + function)
            self.function = function
            if subprocess.call(["irsend", "SEND_ONCE", "heat_pump", command]) == 0:
                reported_state = {'function': function}
                message = {'state': {'reported': reported_state}}
                raw_message = json.dumps(message)
                try:
                    self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
                except Exception:
                    self.logger.warning('publish timeout, clearing local state')
                    self.humidity = None
                    self.temperature = None
            else:
                self.logger.warning('could not send command to heat pump')

    def process_state(self, state):
        """Determine what action (if any) to take based on the most recent state change"""
        try:
            current_temperature = state['temperature']
            if current_temperature > self.cooling_start:
                self.heatpump_command('cooling')

            elif current_temperature < self.heating_start:
                self.heatpump_command('heating')

            elif current_temperature > self.heating_stop and current_temperature < self.cooling_stop:
                self.heatpump_command('shutdown')

        except KeyError:
            pass

    def send_set_points(self):
        """Send set points to IoT"""
        message = {
            'state': {
                'reported': {
                    'cooling_start': self.cooling_start,
                    'cooling_stop': self.cooling_stop,
                    'heating_start': self.heating_start,
                    'heating_stop': self.heating_stop
                }
            }
        }
        raw_message = json.dumps(message)
        try:
            self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
        except Exception:
            self.logger.warning('publish timeout, clearing local state')
            self.humidity = None
            self.temperature = None

    def send_sample(self):
        """Send state to IoT"""
        GPIO.output(DHT_ONOFF_PIN, 1)
        time.sleep(2)
        humidity1, temperature1 = Adafruit_DHT.read_retry(SENSOR, DHT_PIN)
        humidity2, temperature2 = Adafruit_DHT.read_retry(SENSOR, DHT_PIN)
        humidity3, temperature3 = Adafruit_DHT.read_retry(SENSOR, DHT_PIN)
        GPIO.output(DHT_ONOFF_PIN, 0)

        temperature = round(numpy.median([temperature1, temperature2, temperature3]), 1)
        humidity = round(numpy.median([humidity1, humidity2, humidity3]), 1)

        reported_state = {}
        now = time.time()
        forced_update = self.last_update is None or now > self.last_update + 60
        self.logger.debug('last_update: ' + str(self.last_update) + ', now: ' + str(now) + ', force update: ' + str(self.last_update is None or now > self.last_update + 60) + ', t: ' + str(temperature) + ', h: ' + str(humidity))
        if humidity is not None:
            humidity = round(humidity, 1)
            if forced_update or self.humidity is None or abs(humidity - self.humidity) > 0.2:
                self.humidity = humidity
                reported_state['humidity'] = humidity
        else:
            self.logger.debug('no humidity')

        if temperature is not None:
            temperature = round(temperature, 1)
            if forced_update or self.temperature is None or abs(temperature - self.temperature) > 0.2:
                self.temperature = temperature
                reported_state['temperature'] = temperature
        else:
            self.logger.debug('no temperature')

        if reported_state != {}:
            self.last_update = now
            message = {'state': {'reported': reported_state}}
            raw_message = json.dumps(message)
            self.logger.debug(raw_message)
            try:
                self.mqtt_client.publish(TOPICS['shadow_update'], raw_message, 1)
            except Exception:
                self.logger.warning('publish timeout, clearing local state')
                self.humidity = None
                self.temperature = None

            return reported_state

        else:
            return None

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
    main()
