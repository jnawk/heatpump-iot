"""IoT Module"""
import time
import logging
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import publishTimeoutException

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
STREAM_HANDLER = logging.StreamHandler()
STREAM_HANDLER.setFormatter(FORMATTER)

logger = logging.getLogger(__name__) # pylint: disable=invalid-name
logger.setLevel(logging.WARNING)
logger.addHandler(STREAM_HANDLER)

def _compute_trend(previous, current):
    return (previous < current) - (current < previous)

def topics(thing):
    """returns a dict containing the topics for a given thing"""
    topic_prefix = '$aws/things/%s/shadow' % thing
    return {
        'shadow_update': '%s/update' % topic_prefix,
        'shadow_update_accepted': '%s/update/accepted' % topic_prefix,
        'shadow_update_rejected': '%s/update/rejected' % topic_prefix,
        'update_state': '%s/delta' % topic_prefix,
        'update_document': '%s/update/documents' % topic_prefix,
        'get_state': '%s/get' % topic_prefix,
        'get_state_accepted': '%s/get/accepted' % topic_prefix,
        'get_state_rejected': '%s/get/rejected' % topic_prefix
    }


class IoT(object):
    """Class to interact with AWS IoT"""
    def __init__(self, client_id):
        self.client_id = client_id
        self.mqtt_client = None

    @property
    def topics(self):
        """The topics for this thing"""
        return topics(self.client_id)

    def connect(self, host, credentials):
        """Connect to the IoT service"""
        logger.debug('connecting...')
        mqtt_client = AWSIoTMQTTClient(self.client_id)
        mqtt_client.configureEndpoint(host, 8883)
        mqtt_client.configureCredentials(credentials.root_ca_path,
                                         credentials.private_key_path,
                                         credentials.certificate_path)

        # AWSIoTMQTTClient connection configuration
        mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
        mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
        mqtt_client.configureMQTTOperationTimeout(30)  # 30 sec

        mqtt_client.connect()
        self.mqtt_client = mqtt_client

    def subscribe(self, topic, callback):
        """Wrapper around mqtt subscribe"""
        def _callback(client, userdata, message):
            message = json.loads(message.payload)
            callback(client, userdata, message)

        logger.debug('subscribing %s', topic)
        self.mqtt_client.subscribe(topic, 1, _callback)

    def publish(self, topic, message):
        """wrapper around mqtt publish"""
        if not isinstance(message, str):
            message['state']['reported']['thing'] = self.client_id
            message = json.dumps(message)
        try:
            self.mqtt_client.publish(topic, message, 1)
        except publishTimeoutException:
            time.sleep(5)
            self.mqtt_client.publish(topic, message, 1)

class Credentials(object):
    """Credentials container"""
    def __init__(self,
                 root_ca_path=None,
                 private_key_path=None,
                 certificate_path=None):
        self._root_ca_path = root_ca_path
        self._private_key_path = private_key_path
        self._certificate_path = certificate_path

    @property
    def root_ca_path(self):
        """Getter for root_ca_path property"""
        return self._root_ca_path

    @property
    def private_key_path(self):
        """Getter for private_key_path property"""
        return self._private_key_path

    @property
    def certificate_path(self):
        """Getter for certificate_path property"""
        return self._certificate_path

class DataItem(object):
    """Class to hold the data about a sample"""
    def __init__(self, value=None, last_update=None, previous_value=None, trend=None):
        if not value:
            raise ValueError('value is required')
        self._value = value
        if last_update:
            self._last_update = last_update
        else:
            self._last_update = time.time()

        self._previous_value = previous_value
        self._trend = trend

    def is_noise(self, new_value):
        """
        Determines whether a new value represents noise in the signal

        Simply, if the value is different in the same direction as the trend, then
        it is not noise, but if the value is only 0.1 against the trend, then it
        is noise.
        """
        if not self.trend:
            logger.debug('no trend')
            return False

        new_trend = _compute_trend(self.value, new_value)
        if new_trend == self.trend:
            logger.debug('same trend')
            return False
        return abs(new_value - self.value) < 0.2

    def compute_trend(self, new_value):
        """Computes the trend this new value represents"""
        return _compute_trend(self.value, new_value)

    @property
    def value(self):
        """The value of this data point"""
        return self._value

    @value.setter
    def value(self, value):
        if not value:
            raise ValueError('value is required')

        self._previous_value = self._value
        self._value = value
        self._last_update = time.time()
        if self._previous_value:
            self._trend = _compute_trend(self._previous_value, value)

    @property
    def trend(self):
        """Whether this data item is trending up or down"""
        return self._trend

    @property
    def last_update(self):
        """The time this data item was last updated"""
        return self._last_update

    def __repr__(self):
        pattern = '%s(value=%r, last_update=%r, previous_value=%r, trend=%r)'
        return pattern % (self.__class__.__name__,
                          self.value,
                          self.last_update,
                          self._previous_value,
                          self.trend)

class TemperatureSensor(object): # pylint: disable=too-few-public-methods
    """Temperature Sensor"""
    def __init__(self, temperature=None):
        self._temperature = temperature

    @property
    def temperature(self):
        """The Temperature"""
        return self._temperature

    @temperature.setter
    def temperature(self, temperature):
        self._set_temperature(temperature)

    def _set_temperature(self, temperature):
        raise NotImplementedError
