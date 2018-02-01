"""Tests for the controller module"""
from __future__ import print_function

import os
import sys
sys.path.append(os.path.dirname('vendored/'))

 # pylint: disable=wrong-import-position
import unittest
from controller import Controller, DEFAULT_SETPOINTS
from heatpump import Heatpump, START_HEATING
from iot import IoT

class ControllerTest(unittest.TestCase):
    """Tests for the Controller class"""
    def setUp(self):
        self.controller = Controller()
        self.controller.humidity = 10
        self.controller.temperature = 10

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
        self.controller.humidity = None
        self.controller.temperature = None

        new_state = {'humidity': 10, 'temperature': 10}
        state_difference = self.controller.compute_state_difference(new_state)

        # no existing temperature
        self.assertIn('temperature', state_difference)

        # no existing humidity
        self.assertIn('humidity', state_difference)

    def test_action_already_happening(self): #pylint: disable=no-self-use
        """
        Verifies the controller doesn't try to tell the heatpump to do what it is
        already doing
        """
        class MockHeatpump(Heatpump):
            """Mock Heatpump implementation which barfs when send_command is called"""
            def send_command(self, command):
                raise AssertionError('The controller should not ask the heatpump \
                to do what it is already doing')

        class MockIoT(IoT):
            """Mock IoT implementation whose publish does nothing"""
            def publish(self, _topic, _message):
                pass

        heatpump = MockHeatpump()
        heatpump.setpoints = DEFAULT_SETPOINTS
        heatpump._current_action = START_HEATING #pylint: disable=protected-access

        iot = MockIoT(None)

        controller = Controller()
        controller.iot = iot
        controller.heatpump = heatpump

        state = {'temperature': 10}
        controller.process_state(state)
