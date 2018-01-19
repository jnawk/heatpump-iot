"""Sensor module"""
import time
import atexit
from numpy import median
import RPi.GPIO as GPIO
import Adafruit_DHT

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

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.onoff_pin, GPIO.OUT)

        atexit.register(GPIO.cleanup)

    def _boot_sensor(self):
        GPIO.output(self.onoff_pin, 1)
        time.sleep(2)

    def _shutdown_sensor(self):
        GPIO.output(self.onoff_pin, 0)

    def read(self):
        """read the sensor"""
        try:
            self._boot_sensor()
            temperature_samples = []
            humidity_samples = []
            tries = 10
            while tries > 0 and len(temperature_samples) < 3 and len(humidity_samples) < 3:
                humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.data_pin)
                if temperature is not None:
                    temperature_samples.append(temperature)
                if humidity is not None:
                    humidity_samples.append(humidity)
            return (round(median(humidity_samples), 1),
                    round(median(temperature_samples), 1))
        finally:
            self._shutdown_sensor()
