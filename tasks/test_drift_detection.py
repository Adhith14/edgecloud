import unittest
class TestDriftDetection(unittest.TestCase):
    def test_no_drift(self):
        rows = [{'mem_pct': 50, 'error_rate': 1}, {'mem_pct': 49, 'error_rate': 2}, {'mem_pct': 48, 'error_rate': 3}]
        self.assertEqual(detect_drift.detect_drift(rows), -1)

    def test_short_data(self):
        rows = [{'mem_pct': 50, 'error_rate': 1}, {'mem_pct': 49, 'error_rate': 2}]
        self.assertEqual(detect_drift.detect_drift(rows), -1)

    def test_drift_at_start(self):
        rows = [{'mem_pct': 60, 'error_rate': 3}, {'mem_pct': 58, 'error_rate': 4}, {'mem_pct': 57, 'error_rate': 5}]
        self.assertEqual(detect_drift.detect_drift(rows), 1)

    def test_drift_in_middle(self):
        rows = [{'mem_pct': 50, 'error_rate': 2}, {'mem_pct': 49, 'error_rate': 3}, {'mem_pct': 51, 'error_rate': 4}]
        self.assertEqual(detect_drift.detect_drift(rows), 2)

if __name__ == '__main__':
    import detect_drift
    import unittest
    unittest.main(argv=['first-arg-is-ignored'], exit=False)