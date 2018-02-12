"""Tests for the controller module"""
from __future__ import print_function

import os
import sys
sys.path.append(os.path.dirname('vendored/'))

# pylint: disable=wrong-import-position
import time
import unittest
import logging
import controller
from controller import Controller, DEFAULT_SETPOINTS, State, DataItem
from heatpump import Heatpump, START_HEATING, START_COOLING
from iot import IoT
from gpio import Sample

STREAM_HANDLER = logging.StreamHandler(sys.stdout)

def capture_logs():
    """Enables logging to stdout.  Call this to debug tests"""
    logger = logging.getLogger('controller')
    logger.level = logging.DEBUG
    logger.addHandler(STREAM_HANDLER)

class ControllerTest(unittest.TestCase):
    """Tests for the Controller class"""
    def setUp(self):
        def _publish(_topic, _message):
            pass
        iot = IoT(None)
        iot.publish = _publish

        heatpump = Heatpump()
        heatpump.setpoints = DEFAULT_SETPOINTS
        heatpump._current_action = START_HEATING #pylint: disable=protected-access

        self.controller = Controller()
        self.controller.state.humidity = 10
        self.controller.state.temperature = 10
        self.controller.heatpump = heatpump
        self.controller.iot = iot

    def tearDown(self):
        logger = logging.getLogger('controller')
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

        state_difference = self.controller.send_sample(Sample(10, 10))
        self.assertIsNotNone(state_difference)

    def test_action_already_happening(self): #pylint: disable=no-self-use
        """
        Verifies the controller doesn't try to tell the heatpump to do what it is
        already doing
        """
        def _send_command(_command):
            self.fail('The controller should not ask the heatpump to do what it is already doing')

        self.controller.heatpump.send_command = _send_command

        state = Sample(temperature=10)
        self.controller.process_state(state)

    def test_action_when_none(self):
        """
        Verifies the controller tells the heatpump to change state when it's not
        currently doing anything
        """
        def _send_command(command):
            self.assertEquals(command, START_HEATING)

        self.controller.heatpump.send_command = _send_command

        state = Sample(temperature=10)
        self.controller.heatpump._current_action = None #pylint: disable=protected-access
        self.controller.process_state(state)

    def test_initial_update(self):
        """Verifies we don't blow up when it's the first run"""
        self.controller.state.reset()
        _ = self.controller.send_sample(Sample(10, 10))

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

        self.controller.heatpump._current_action = START_COOLING #pylint: disable=protected-access

        with(self.assertRaises(_CommandSent)):
            self.controller.process_state(Sample(temperature=26))

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
            self.controller.process_state(Sample(temperature=8))

class StateTest(unittest.TestCase):
    """Tests for the State class"""
    def setUp(self):
        self.state = State()

    def test_last_update(self):
        """
        Verifies the last_update property takes on the value of the older of the
        two dimensions.
        """
        self.state.temperature = 10
        time.sleep(0.01)
        self.state.humidity = 10

        self.assertEquals(self.state.last_update, self.state._temperature.last_update) #pylint: disable=protected-access

class ComputeTrendTest(unittest.TestCase):
    """Tests for the _compute_trend method"""
    def setUp(self):
        pass

    #pylint: disable=protected-access
    def test_positive(self):
        """
        Verifies _compute_trend returns 1 when the new value is higher than the
        old
        """
        self.assertEquals(controller._compute_trend(10, 20), 1)

    def test_flat(self):
        """
        Verifies _compute_trend returns 0 when the new value is the same as the
        old
        """
        self.assertEquals(controller._compute_trend(10, 10), 0)

    def test_negative(self):
        """
        Verifies _compute_trend returns -1 when the new value is lower than the
        old
        """
        self.assertEquals(controller._compute_trend(20, 10), -1)

class DataItemTest(unittest.TestCase):
    """Tests for the DataItem class"""
    def setUp(self):
        self.data_item = DataItem(20)

    def test_noise_no_trend(self):
        """Verifies no value is noise when there is no previous value"""
        self.assertFalse(self.data_item.is_noise(20))
        self.assertFalse(self.data_item.is_noise(20.1))
        self.assertFalse(self.data_item.is_noise(10))

    def test_noise_noisy(self):
        """Verifies a small difference is reported as noise"""
        self.data_item.value = 21 # trend is up
        self.assertTrue(self.data_item.is_noise(20.9))
        self.assertFalse(self.data_item.is_noise(21.1))

        self.data_item.value = 20 # trend is down
        self.assertTrue(self.data_item.is_noise(20.1))
        self.assertFalse(self.data_item.is_noise(19.9))

    def test_noise_not_noisy(self):
        """Verifies large differences are not reported as noise"""
        self.data_item.value = 21 # trend is up
        self.assertFalse(self.data_item.is_noise(22))
        self.assertFalse(self.data_item.is_noise(20))

        self.data_item.value = 20 # trend is down
        self.assertFalse(self.data_item.is_noise(21))
        self.assertFalse(self.data_item.is_noise(19))

    def test_trend_up(self):
        """Verifies trend is up when trend is up"""
        self.assertEquals(self.data_item.compute_trend(20.1), 1)

    def test_trend_same(self):
        """Verifies trend is flat when trend is flat"""
        self.assertEquals(self.data_item.compute_trend(20), 0)

    def test_trend_down(self):
        """Verifies trend is down when trend is down"""
        self.assertEquals(self.data_item.compute_trend(19.9), -1)
