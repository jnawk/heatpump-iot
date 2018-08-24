"""Test cases for heatpump"""
import os
import sys
sys.path.append(os.path.dirname('vendored/'))

# pylint: disable=wrong-import-position
import unittest
import heatpump_controller
import heatpump as hp

class HeatpumpTest(unittest.TestCase):
    """Test cases for Heatpump"""
    def setUp(self):
        self.heatpump = hp.Heatpump()
        self.heatpump.setpoints = heatpump_controller.DEFAULT_SETPOINTS

    def test_action_hot(self):
        """Verifies that when it is stinking hot, the action is to start cooling"""
        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.C1] + 0.1)
        self.assertEquals(hp.START_COOLING, action)

    def test_action_warm(self):
        """
        Verifies that when it is merely warm, there is no action to take - whatever
        we are currently doing, be it cooling, heating, or nothing at all, we will
        continue doing that.
        """

        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.C0] + 0.1)
        self.assertIsNone(action)

    def test_action_cool(self):
        """
        Verifies that when it is merely cool, there is no action to take - whatever
        we are currently doing, be it cooling, heating, or nothing at all, we will
        continue doing that.
        """

        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.H0] - 0.1)
        self.assertIsNone(action)

    def test_action_cold(self):
        """Verifies that when it's as cold as hell, the action is to start heating"""

        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.H1] - 0.1)
        self.assertEquals(hp.START_HEATING, action)

    def test_action_shutdown(self):
        """Verifies that when it's in the goldielocks zone, the action is to shutdown"""

        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.H0] + 0.1)
        self.assertEquals(hp.SHUTDOWN, action)

        action = self.heatpump.get_action(heatpump_controller.DEFAULT_SETPOINTS[hp.C0] - 0.1)
        self.assertEquals(hp.SHUTDOWN, action)

    def test_set_missing_param(self):
        """Verifies the setter hurls when given missing setpoints"""
        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.H1: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.H0: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.C0: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.C1: None}

    def test_set_crazy_params(self):
        """Verifies the heatpump barfs when given backards values"""
        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.H1: 10, hp.H0: 5}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.C0: 10, hp.C1: 5}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {hp.H0: 10, hp.C0: 5}
