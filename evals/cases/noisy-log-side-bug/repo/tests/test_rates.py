import unittest

from metrics.rates import per_second


class RateTests(unittest.TestCase):
    def test_per_second(self):
        self.assertEqual(per_second(120, 60), 2.0)


if __name__ == "__main__":
    unittest.main()
