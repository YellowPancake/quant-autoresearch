import math
import unittest
from core import indicators as ind


class IndicatorTests(unittest.TestCase):
    def test_hand_calculated_values(self):
        self.assertEqual(ind.sma([1, 2, 3, 6], 3), [None, None, 2, 11/3])
        self.assertEqual(ind.ema([1, 2, 3, 6], 3), [None, None, 2, 4])
        bands = ind.boll([1, 2, 3], 3)
        self.assertEqual(bands['middle'][-1], 2)
        self.assertAlmostEqual(bands['upper'][-1], 2 + 2*math.sqrt(2/3))
        self.assertEqual(ind.rsi([1, 2, 3, 2], 2), [None, None, 100, 50])
        self.assertEqual(ind.rsi([1, 1, 1], 2)[-1], 50)
        self.assertEqual(ind.atr([11, 13, 14], [9, 10, 11], [10, 12, 13], 2), [None, None, 3])
        self.assertAlmostEqual(ind.roc([100, 110])[-1], .1)
        self.assertAlmostEqual(ind.volatility([1, 2, 2], 2, 1)[-1], math.sqrt(.5))
        self.assertEqual(ind.volume_ratio([10, 20, 60], 2), [None, None, 4])
        self.assertEqual(ind.donchian([2, 4, 3], [1, 2, 2], 2), {'upper': [None, 4, 4], 'lower': [None, 1, 2]})

    def test_macd_warmup_and_convention(self):
        output = ind.macd(list(range(1, 41)))
        self.assertTrue(all(v is None for v in output['dea'][:33]))
        self.assertAlmostEqual(output['dif'][33], 7)
        self.assertAlmostEqual(output['dea'][33], 7)
        self.assertAlmostEqual(output['hist'][33], 0)
        output = ind.macd(list(range(1, 35)) + [80, 40, 60])
        self.assertAlmostEqual(output['hist'][-1], 2*(output['dif'][-1]-output['dea'][-1]))

    def test_missing_values_and_invalid_input(self):
        self.assertEqual(ind.ema([1, 2, None, 4, 6], 2), [None, 1.5, None, None, 5])
        self.assertEqual(ind.volume_ratio([0, 0, 3], 2), [None]*3)
        for function in (ind.sma, ind.ema, ind.rsi, ind.roc, ind.volatility, ind.volume_ratio):
            self.assertEqual(function([]), [])
            with self.assertRaises(ValueError): function([1, float('nan')])
            with self.assertRaises(ValueError): function([1, 2], period=0)
        with self.assertRaises(ValueError): ind.atr([1], [], [1])
        with self.assertRaises(ValueError): ind.macd([1], fast=26, slow=12)

    def test_future_extension_never_changes_past(self):
        close = [20 + i*.1 + math.sin(i) for i in range(80)]
        functions = [ind.sma, ind.ema, ind.macd, ind.boll, ind.rsi, ind.roc, ind.volatility,
                     lambda c: ind.atr([x+1 for x in c], [x-1 for x in c], c),
                     lambda c: ind.donchian([x+1 for x in c], [x-1 for x in c]), ind.volume_ratio]
        for function in functions:
            short, long = function(close[:50]), function(close)
            if isinstance(short, dict):
                for key in short: self.assertEqual(short[key], long[key][:50])
            else:
                self.assertEqual(short, long[:50])


if __name__ == '__main__':
    unittest.main()
