"""Tests for the controller module"""
from __future__ import print_function

import unittest
from controller import Controller

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

if __name__ == '__main__':
    unittest.main()
