"""Accounting invariants and cross-study consistency for the unified report."""
import csv
import unittest
from pathlib import Path

from evaluate import FEE, simulate, metrics, assess

HERE = Path(__file__).resolve().parent


class AccountingTests(unittest.TestCase):
    def test_next_close_and_purchase_cost(self):
        prices = [{'date': f'2023-01-0{i+3}', 'asset': v} for i, v in enumerate([100, 200, 220])]
        curve = simulate(prices, {'2023-01-04': {'asset': 1}})
        self.assertEqual(curve[0]['equity'], 1)
        self.assertAlmostEqual(curve[1]['equity'], 1 / (1 + FEE))
        self.assertAlmostEqual(curve[2]['equity'], 1.1 / (1 + FEE))

    def test_cash_does_not_receive_dividend_return(self):
        prices = [{'date': '2023-01-03', 'asset': 100}, {'date': '2023-01-04', 'asset': 110}]
        self.assertEqual(simulate(prices, {})[-1]['equity'], 1)

    def test_exit_fee_and_no_terminal_sale(self):
        prices = [{'date': f'2023-01-0{i+3}', 'asset': 100} for i in range(3)]
        held = simulate(prices, {'2023-01-04': {'asset': 1}})
        sold = simulate(prices, {'2023-01-04': {'asset': 1}, '2023-01-05': {}})
        self.assertAlmostEqual(held[-1]['equity'], 1 / (1 + FEE))
        self.assertAlmostEqual(sold[-1]['equity'], (1 - FEE) / (1 + FEE))

    def test_missing_quote_carries_mark_but_cannot_execute(self):
        prices = [{'date': f'2023-01-0{i+3}', 'asset': v} for i, v in enumerate([100, 100, '', 110])]
        curve = simulate(prices, {'2023-01-04': {'asset': 1}})
        self.assertEqual(curve[1]['equity'], curve[2]['equity'])
        self.assertAlmostEqual(curve[3]['equity'], 1.1 / (1 + FEE))
        with self.assertRaises(AssertionError):
            simulate(prices, {'2023-01-05': {'asset': 1}})

    def test_calendar_annualization_and_drawdown(self):
        m = metrics([{'date': '2023-01-01', 'equity': 1}, {'date': '2023-06-01', 'equity': .8},
                     {'date': '2024-01-01', 'equity': 1.2}])
        self.assertAlmostEqual(m['annual_return'], 1.2 ** (365.2425 / 365) - 1)
        self.assertAlmostEqual(m['max_drawdown'], .2)

    def test_china_baseline_is_identical_every_day(self):
        curves = []
        for market in ('csi300', 'broad_market'):
            with (HERE / market / 'equity.csv').open() as f:
                curves.append([(r['partition'], r['date'], r['equity']) for r in csv.DictReader(f)
                               if r['attempt'] == 'baseline_csi300'])
        self.assertEqual(len(curves[0]), 1624)
        self.assertEqual(curves[0], curves[1])

    def test_original_constraint_boundaries_are_preserved(self):
        result = {'annual_return': .6, 'total_return': 1, 'max_drawdown': .5}
        self.assertFalse(assess('csi300', result)['feasible'])
        self.assertTrue(assess('sp500', result)['target_met'])
        result.update(annual_return=.3, max_drawdown=.314)
        self.assertFalse(assess('broad_market', result)['feasible'])
        result['max_drawdown'] = .3134
        self.assertTrue(assess('broad_market', result)['target_met'])


if __name__ == '__main__':
    unittest.main()
