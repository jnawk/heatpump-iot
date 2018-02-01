import unittest
from controller import DEFAULT_SETPOINTS
from heatpump import *

class HeatpumpTest(unittest.TestCase):
    def setUp(self):
        self.heatpump = Heatpump()
        self.heatpump.setpoints = DEFAULT_SETPOINTS

    def test_action_hot(self):
        """Verifies that when it is stinking hot, the action is to start cooling"""
        action = self.heatpump.get_action(DEFAULT_SETPOINTS[C1] + 0.1)
        self.assertEquals(START_COOLING, action)

    def test_action_warm(self):
        """
        Verifies that when it is merely warm, there is no action to take - whatever
        we are currently doing, be it cooling, heating, or nothing at all, we will
        continue doing that.
        """

        action = self.heatpump.get_action(DEFAULT_SETPOINTS[C0] + 0.1)
        self.assertIsNone(action)

    def test_action_cool(self):
        """
        Verifies that when it is merely cool, there is no action to take - whatever
        we are currently doing, be it cooling, heating, or nothing at all, we will
        continue doing that.
        """

        action = self.heatpump.get_action(DEFAULT_SETPOINTS[H0] - 0.1)
        self.assertIsNone(action)

    def test_action_cold(self):
        """Verifies that when it's as cold as hell, the action is to start heating"""

        action = self.heatpump.get_action(DEFAULT_SETPOINTS[H1] - 0.1)
        self.assertEquals(START_HEATING, action)

    def test_action_shutdown(self):
        """Verifies that when it's in the goldielocks zone, the action is to shutdown"""

        action = self.heatpump.get_action(DEFAULT_SETPOINTS[H0] + 0.1)
        self.assertEquals(SHUTDOWN, action)

        action = self.heatpump.get_action(DEFAULT_SETPOINTS[C0] - 0.1)
        self.assertEquals(SHUTDOWN, action)

    def test_set_missing_param(self):
        """Verifies the setter hurls when given missing setpoints"""
        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {H1: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {H0: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {C0: None}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {C1: None}

    def test_set_crazy_params(self):
        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {H1: 10, H0: 5}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {C0: 10, C1: 5}

        with self.assertRaises(ValueError):
            self.heatpump.setpoints = {H0: 10, C0: 5}
