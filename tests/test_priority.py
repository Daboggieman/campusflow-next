import unittest
from datetime import datetime
from campusflow.priority import calculate_priority

class TestCalculatePriority(unittest.TestCase):
    def test_critical_priority(self):
        self.assertEqual(calculate_priority("high", 10), "critical")

    def test_high_priority(self):
        self.assertEqual(calculate_priority("high", 9), "high")

    def test_medium_priority(self):
        self.assertEqual(calculate_priority("medium", 3), "medium")

    def test_low_priority(self):
        self.assertEqual(calculate_priority("low", 1), "low")