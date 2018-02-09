"""Sensor module"""
import time
import atexit
from numpy import median
try:
    import RPi.GPIO as GPIO #pylint: disable=import-error
    import Adafruit_DHT #pylint: disable=import-error
except ImportError:
    import inspect
    def _in_unittest():
        current_stack = inspect.stack()
        for stack_frame in current_stack:
            if "unittest" in stack_frame[1]:
                return True
        return False
    if not _in_unittest():
        raise

ON = 1
OFF = 0

class Sensor(object):
    """Sensor class"""
    def __init__(self,
                 sensor,
                 data_pin,
                 onoff_pin):
        """Constructor"""
        self.sensor = sensor
        self.data_pin = data_pin
        self.onoff_pin = onoff_pin
        self._sensor_state = OFF

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.onoff_pin, GPIO.OUT)

        atexit.register(GPIO.cleanup)

    @property
    def sensor_state(self):
        """State of sensor"""
        return self._sensor_state

    @sensor_state.setter
    def sensor_state(self, sensor_state):
        if self._sensor_state == sensor_state:
            return

        if sensor_state != ON and sensor_state != OFF:
            raise ValueError('Sensor state can only be ON or OFF')

        GPIO.output(self.onoff_pin, sensor_state)
        self._sensor_state = sensor_state
        if sensor_state == ON:
            time.sleep(2)

    @property
    def current_sample(self):
        """Reads the sensor and returns the current samples"""
        old_sensor_state = self.sensor_state
        try:
            self.sensor_state = ON
            return Adafruit_DHT.read_retry(self.sensor, self.data_pin)
        finally:
            self.sensor_state = old_sensor_state

    @property
    def sample(self):
        """read the sensor"""
        try:
            # turn on sensor so the sampler doesn't turn it off
            self.sensor_state = ON
            samples = Samples()
            tries_remaining = 10
            while tries_remaining > 0 and samples.sample_count < 3:
                samples.humidity, samples.temperature = self.current_sample
                tries_remaining = tries_remaining - 1
            return Sample(samples.humidity, samples.temperature)
        finally:
            self.sensor_state = OFF

class Sample(object):
    """Sample class"""
    def __init__(self, humidity, temperature):
        self._humidity = humidity
        self._temperature = temperature

    @property
    def humidity(self):
        """The humidity"""
        return self._humidity

    @property
    def temperature(self):
        """The temperature"""
        return self._temperature

class Samples(object):
    """Samples class"""
    def __init__(self):
        self._temperature = []
        self._humidity = []

    @property
    def sample_count(self):
        """Minimum number of samples collected"""
        return min(len(self._temperature), len(self._humidity))

    @property
    def temperature(self):
        """Average temperature"""
        if not self._temperature:
            return None

        return round(median(self._temperature), 1)

    @property
    def humidity(self):
        """Average humidity"""
        if not self._humidity:
            return None

        return round(median(self._humidity), 1)

    @temperature.setter
    def temperature(self, temperature):
        if temperature is not None:
            self._temperature.append(temperature)

    @humidity.setter
    def humidity(self, humidity):
        if humidity is not None:
            self._humidity.append(humidity)
