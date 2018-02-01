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
class IoT(object):
    """Class to interact with AWS IoT"""
    def __init__(self, client_id):
        self.client_id = client_id
        self.mqtt_client = None

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
        mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec

        mqtt_client.connect()
        self.mqtt_client = mqtt_client

    def subscribe(self, topic, callback):
        """Wrapper around mqtt subscribe"""
        def _callback(client, userdata, message):
            message = json.loads(message.payload)
            callback(client, userdata, message)

        self.mqtt_client.subscribe(topic, 1, _callback)

    def publish(self, topic, message):
        """wrapper around mqtt publish"""
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
    def private_key_paty(self):
        """Getter for private_key_path property"""
        return self._private_key_path

    @property
    def certificate_path(self):
        """Getter for certificate_path property"""
        return self._certificate_path
