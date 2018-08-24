"""Tests for the iot module"""
import os
import sys
sys.path.append(os.path.dirname('vendored/'))

# pylint: disable=wrong-import-position
import unittest
import iot

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
        self.assertEquals(iot._compute_trend(10, 20), 1)

    def test_flat(self):
        """
        Verifies _compute_trend returns 0 when the new value is the same as the
        old
        """
        self.assertEquals(iot._compute_trend(10, 10), 0)

    def test_negative(self):
        """
        Verifies _compute_trend returns -1 when the new value is lower than the
        old
        """
        self.assertEquals(iot._compute_trend(20, 10), -1)

class DataItemTest(unittest.TestCase):
    """Tests for the DataItem class"""
    def setUp(self):
        self.data_item = iot.DataItem(20)

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
