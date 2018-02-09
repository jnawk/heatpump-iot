"""Sensor module"""
import time
import atexit
from numpy import median
try:
    import RPi.GPIO as GPIO #pylint: disable=import-error
    import Adafruit_DHT #pylint: disable=import-error
    atexit.register(GPIO.cleanup)
    GPIO.setmode(GPIO.BCM)
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

class LEDVerify(object):
    """Class for reading the 74HC373N"""
    def __init__(self, le_pin, d0_pin, q0_pin):
        GPIO.setup(le_pin, GPIO.OUT)
        GPIO.setup(d0_pin, GPIO.OUT)
        GPIO.setup(q0_pin, GPIO.IN)
        self.le_pin = le_pin
        self.d0_pin = d0_pin
        self.q0_pin = q0_pin

        self.self_test()

    @property
    def state(self):
        """Reads Q0 from the 74HC373N"""
        return GPIO.input(self.q0_pin)

    def reset(self):
        """
        Resets the memory state for another read

        Ensure this is never run concurrently with the LEDs
        """
        GPIO.output(self.d0_pin, GPIO.LOW)
        GPIO.output(self.le_pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.le_pin, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.d0_pin, GPIO.HIGH)

    def self_test(self):
        """
        Performs a self test

        Ensure this is never run concurrently with the LEDs
        """
        # reset - state should be LOW
        self.reset()
        if self.state != GPIO.LOW:
            raise IOError('1/3: GPIO State was not LOW')

        # Simulate LED firing - state should be HIGH
        GPIO.output(self.le_pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.le_pin, GPIO.LOW)

        # reset - state should be LOW
        if self.state != GPIO.HIGH:
            raise IOError('2/3: GPIO State was not HIGH')

        self.reset()
        if self.state != GPIO.LOW:
            raise IOError('3/3: GPIO State was not LOW)')

class DHT22(object):
    """DHT22 Sensor class"""
    def __init__(self, data_pin, onoff_pin):
        """Constructor"""
        GPIO.setup(onoff_pin, GPIO.OUT)
        self.data_pin = data_pin
        self.onoff_pin = onoff_pin
        self._sensor_state = OFF

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
            return Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.data_pin)
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
