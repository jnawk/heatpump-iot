"""Tests for the controller module"""
import os
import sys
sys.path.append(os.path.dirname('vendored/'))

# pylint: disable=wrong-import-position
import time
import unittest
import logging

import heatpump_controller
import heatpump as hp
import gpio

from iot import IoT

STREAM_HANDLER = logging.StreamHandler(sys.stdout)

def capture_logs():
    """Enables logging to stdout.  Call this to debug tests"""
    logger = logging.getLogger('heatpump_controller')
    logger.level = logging.DEBUG
    logger.addHandler(STREAM_HANDLER)

class HeatpumpControllerTest(unittest.TestCase):
    """Tests for the Controller class"""
    def setUp(self):
        iot = IoT(None)
        iot.publish = lambda a, b: None

        heatpump = hp.Heatpump()
        heatpump.led_verify = object()
        heatpump.setpoints = heatpump_controller.DEFAULT_SETPOINTS
        heatpump._current_action = hp.START_HEATING #pylint: disable=protected-access

        self.controller = heatpump_controller.HeatpumpController({
            'log_level': 'DEBUG',
            'dht':{
                'data_pin': None,
                'onoff_pin': None
            },
            'led_verify':{
                'le_pin': None,
                'd0_pin': None,
                'q0_pin': None
            },
            'default_setpoints': heatpump_controller.DEFAULT_SETPOINTS
        })
        self.controller.state.humidity = 10
        self.controller.state.temperature = 10
        self.controller.heatpump = heatpump
        self.controller.iot = iot

    def tearDown(self):
        logger = logging.getLogger('heatpump_controller')
        logger.removeHandler(STREAM_HANDLER)

    def test_obvious_state_difference(self):
        """
        Verifies that the argument is not modified, and that only the differences
        are in the output
        """
        new_state = {'humidity': 20, 'temperature': 10}
        state_difference = self.controller.compute_state_difference(new_state)

        # don't want the argument to be modified
        self.assertIn('temperature', new_state)

        # humidity was different, it needs to be in the output
        self.assertIn('humidity', state_difference)

        # temperature was not changed
        self.assertNotIn('temperature', state_difference)

    def test_subtle_state_difference(self):
        """Verifies that a small difference is not counted as a difference"""
        new_state = {'humidity': 10, 'temperature': 10.1}
        state_difference = self.controller.compute_state_difference(new_state)

        # 0.1 degree is too small a difference to care about
        self.assertNotIn('temperature', state_difference)

    def test_no_current_state(self):
        """Verifies that when state is not held, new state is returned"""
        self.controller.state.reset()

        new_state = {'humidity': 10, 'temperature': 10}
        state_difference = self.controller.compute_state_difference(new_state)

        # no existing temperature
        self.assertIn('temperature', state_difference)

        # no existing humidity
        self.assertIn('humidity', state_difference)

    def test_stale_state(self):
        """
        Verifies that when the latest update was too long ago, non-changed state
        is included
        """
        def _publish(_topic, message):
            self.assertIn('temperature', message['state']['reported'])

        self.controller.iot.publish = _publish

        last_update = time.time() - 70
        self.controller.state._temperature._last_update = last_update #pylint: disable=protected-access
        self.assertEquals(last_update, self.controller.state.last_update)

        state_difference = self.controller.send_sample(gpio.Sample(10, 10))
        self.assertIsNotNone(state_difference)

    def test_action_already_happening(self): #pylint: disable=no-self-use
        """
        Verifies the controller doesn't try to tell the heatpump to do what it is
        already doing
        """
        def _send_command(_command):
            self.fail('The controller should not ask the heatpump to do what it is already doing')

        self.controller.heatpump.send_command = _send_command

        state = gpio.Sample(temperature=10)
        self.controller.process_state(state)

    def test_action_when_none(self):
        """
        Verifies the controller tells the heatpump to change state when it's not
        currently doing anything
        """
        def _send_command(command):
            self.assertEquals(command, hp.START_HEATING)

        self.controller.heatpump.send_command = _send_command

        state = gpio.Sample(temperature=10)
        self.controller.heatpump._current_action = None #pylint: disable=protected-access
        self.controller.process_state(state)

    def test_initial_update(self):
        """Verifies we don't blow up when it's the first run"""
        self.controller.state.reset()
        _ = self.controller.send_sample(gpio.Sample(10, 10))

    def test_trend_continues_up(self):
        """
        Verifies when the trend is up and the action is to cool that we continue
        to send the cool command
        """
        class _CommandSent(Exception):
            pass

        def _send_command(_command):
            raise _CommandSent()
        self.controller.heatpump.send_command = _send_command

        self.controller.state.temperature = 25 # trend = up!
        self.assertEquals(self.controller.state.temperature.trend, 1)

        self.controller.heatpump._current_action = hp.START_COOLING #pylint: disable=protected-access

        with(self.assertRaises(_CommandSent)):
            self.controller.process_state(gpio.Sample(temperature=26))

    def test_trend_continues_down(self):
        """
        Verifies when the trend is down and the action is to heat that we continue
        to send the cool command
        """
        class _CommandSent(Exception):
            pass

        def _send_command(_command):
            raise _CommandSent()
        self.controller.heatpump.send_command = _send_command

        self.controller.state.temperature = 9 # trend = down
        self.assertEquals(self.controller.state.temperature.trend, -1)

        #self.controller.heatpump._current_action = START_COOLING #pylint: disable=protected-access

        with(self.assertRaises(_CommandSent)):
            self.controller.process_state(gpio.Sample(temperature=8))

class StateTest(unittest.TestCase):
    """Tests for the State class"""
    def setUp(self):
        self.state = heatpump_controller.State()

    def test_last_update(self):
        """
        Verifies the last_update property takes on the value of the older of the
        two dimensions.
        """
        self.state.temperature = 10
        time.sleep(0.01)
        self.state.humidity = 10

        self.assertEquals(self.state.last_update, self.state._temperature.last_update) #pylint: disable=protected-access
