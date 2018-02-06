"""Tests for the controller module"""
from __future__ import print_function

import os
import sys
sys.path.append(os.path.dirname('vendored/'))

 # pylint: disable=wrong-import-position
import time
import unittest
from controller import Controller, DEFAULT_SETPOINTS, State
from heatpump import Heatpump, START_HEATING
from iot import IoT
from sensor import Sample

# need this
class publishTimeoutException(Exception): pass
import controller
controller.publishTimeoutException = publishTimeoutException

class ControllerTest(unittest.TestCase):
    """Tests for the Controller class"""
    def setUp(self):
        def publish(_topic, _message):
            pass

        iot = IoT(None)
        iot.publish = publish

        heatpump = Heatpump()
        heatpump.setpoints = DEFAULT_SETPOINTS
        heatpump._current_action = START_HEATING #pylint: disable=protected-access

        self.controller = Controller()
        self.controller.state.humidity = 10
        self.controller.state.temperature = 10
        self.controller.heatpump = heatpump
        self.controller.iot = iot

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
        def publish(_topic, message):
            self.assertIn('temperature', message['state']['reported'])

        self.controller.iot.publish = publish

        last_update = time.time() - 70
        self.controller.state._temperature['update'] = last_update
        self.assertEquals(last_update, self.controller.state.last_update)

        new_state = {'humidity': 10, 'temperature': 10}
        state_difference = self.controller.send_sample(Sample(10, 10))
        self.assertIsNotNone(state_difference)

    def test_action_already_happening(self): #pylint: disable=no-self-use
        """
        Verifies the controller doesn't try to tell the heatpump to do what it is
        already doing
        """

        def send_command(command):
            fail('The controller should not ask the heatpump to do what it is already doing')

        self.controller.heatpump.send_command = send_command

        state = {'temperature': 10}
        self.controller.process_state(state)

    def test_action_when_none(self): #pylint: disable=no-self-use
        """
        Verifies the controller tells the heatpump to change state when it's not
        currently doing anything
        """
        def send_command(command):
            self.assertEquals(command, START_HEATING)

        self.controller.heatpump.send_command = send_command

        state = {'temperature': 10}
        self.controller.heatpump._current_action = None
        #with self.assertRaises(SendCommandCalled):
        self.controller.process_state(state)

class StateTest(unittest.TestCase):
    def setUp(self):
        self.state = State()

    def test_last_update(self):
        self.state.temperature = 10
        time.sleep(0.01)
        self.state.humidity = 10

        self.assertEquals(self.state.last_update, self.state._temperature['update'])
