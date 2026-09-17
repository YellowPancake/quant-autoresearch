"""Replot the archived strategy against two buy-once benchmarks; no strategy search."""
import argparse
import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, PercentFormatter

ROOT = Path(__file__).resolve().parent


def read_csv(name):
    with (ROOT / name).open() as handle:
        return list(csv.DictReader(handle))


def metrics(values, dates):
    peak = values[0]
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = max(drawdown, 1 - value / peak)
    years = (dates[-1] - dates[0]).days / 365.2425
    return dict(total_return=values[-1] / values[0] - 1,
                annual_return=(values[-1] / values[0]) ** (1 / years) - 1,
                max_drawdown=drawdown)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'figures')
    args = parser.parse_args()
    archived = read_csv('best_methods_test_curves.csv')
    prices = read_csv('benchmark_closes.csv')
    stages = read_csv('stage_metrics.csv')
    sources = json.loads((ROOT / 'benchmark_sources.json').read_text())
    assert hashlib.sha256((ROOT / 'benchmark_closes.csv').read_bytes()).hexdigest() == sources['benchmark_closes_sha256']
    assert [r['date'] for r in archived] == [r['date'] for r in prices]
    dates = [date.fromisoformat(r['date']) for r in archived]
    assert dates == sorted(set(dates)) and len(dates) == 896
    fee = sources['fee_per_side']
    curves = {'strategy_equity': [float(r['strategy_equity']) for r in archived]}
    for key in ('chinext', 'csi300'):
        closes = [float(r[f'{key}_close']) for r in prices]
        assert all(math.isfinite(p) and p > 0 for p in closes)
        # Signal at first close, buy at second close. Units + purchase fee cost 1.
        units = 1 / ((1 + fee) * closes[1])
        curves[f'{key}_equity'] = [1.0] + [units * p for p in closes[1:]]
    summary = {key: metrics(values, dates) for key, values in curves.items()}
    selected = next(r for r in stages if r['attempt'] == '0162')
    for key, value in summary['strategy_equity'].items():
        assert math.isclose(value, float(selected[f'test_{key}']), abs_tol=1e-12)
    assert all(values[0] == 1 for values in curves.values())
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'test_equity.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=['date', *curves])
        writer.writeheader()
        writer.writerows({'date': str(d), **{k: v[i] for k, v in curves.items()}}
                        for i, d in enumerate(dates))
    (args.output / 'comparison_metrics.json').write_text(json.dumps(summary, indent=2) + '\n')
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 10,
        'axes.labelsize': 10, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'axes.linewidth': .8, 'axes.edgecolor': '#222222', 'text.color': '#222222',
        'axes.labelcolor': '#222222', 'xtick.color': '#222222', 'ytick.color': '#222222',
        'xtick.direction': 'in', 'ytick.direction': 'in', 'svg.fonttype': 'none',
        'pdf.fonttype': 42, 'savefig.facecolor': 'white', 'axes.unicode_minus': False})

    def grid(ax):
        ax.grid(True, color='#DADADA', linestyle=':', linewidth=.55)
        ax.set_axisbelow(True)
        ax.tick_params(top=True, right=True)

    def equity(ax):
        grid(ax)
        for key, label, color in [
            ('strategy_equity', 'Strategy #162 (post hoc)', '#D95F02'),
            ('chinext_equity', 'ChiNext ETF buy-and-hold', '#2CA02C'),
            ('csi300_equity', 'CSI 300 TR buy-and-hold', '#1F77B4')]:
            ax.plot(dates, curves[key], color=color, lw=1.6 if key == 'strategy_equity' else 1.45, label=label)
        ax.set_xlim(dates[0], dates[-1])
        ax.set_ylabel('Net asset value (initial = 1)')
        ax.set_xlabel('Date', labelpad=8)
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    def save(fig, name):
        for ext in ('png', 'pdf', 'svg'):
            fig.savefig(args.output / f'{name}.{ext}', dpi=240)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.8, 5.7))
    fig.subplots_adjust(left=.09, right=.975, bottom=.25, top=.88)
    fig.suptitle('Broad-Market Indices: Test-Period Equity Curves', y=.97, fontsize=15)
    equity(ax)
    fig.legend(*ax.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.53, .13),
               ncol=3, frameon=False, fontsize=8.5, handlelength=2.5, columnspacing=1.4)
    fig.text(.53, .065, 'Costs: 0.03% per side. Benchmarks buy once and hold; no terminal sale.', ha='center', fontsize=9)
    fig.text(.53, .027, 'Post-hoc selection among 18 milestones; frozen research champion remains #478.', ha='center', fontsize=9)
    save(fig, 'test_equity')

    fig = plt.figure(figsize=(10.8, 11.8))
    eq = fig.add_axes([.09, .655, .885, .27])
    ret = fig.add_axes([.09, .365, .885, .195])
    dd = fig.add_axes([.09, .14, .885, .195], sharex=ret)
    fig.suptitle('Broad-Market Indices: Test Equity and Research Progress', y=.972, fontsize=15)
    equity(eq)
    fig.legend(*eq.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.53, .601),
               ncol=3, frameon=False, fontsize=8.5, handlelength=2.5, columnspacing=1.4)
    xs = list(range(1, len(stages) + 1))
    for prefix, label, color, marker in [('validation', 'Validation (2020–2022)', '#D95F02', 's'),
                                        ('test', 'Test (2023–2026-09-11)', '#1F77B4', 'o')]:
        style = dict(color=color, linewidth=1.45, marker=marker, markersize=3.8,
                     markerfacecolor='white', markeredgewidth=.9)
        ret.plot(xs, [float(r[f'{prefix}_annual_return']) for r in stages], label=label, **style)
        dd.plot(xs, [float(r[f'{prefix}_max_drawdown']) for r in stages], **style)
    ret.set_ylabel('Annualized net return')
    dd.set_ylabel('Maximum drawdown')
    ret.set_ylim(-.1, .5)
    dd.set_ylim(0, .6)
    for ax in (ret, dd):
        grid(ax)
        ax.set_xlim(.75, len(stages) + .25)
        ax.set_xticks(xs)
        ax.yaxis.set_major_locator(MultipleLocator(.1))
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    plt.setp(ret.get_xticklabels(), visible=False)
    dd.set_xlabel('Stage', labelpad=8)
    fig.legend(*ret.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.53, .086),
               ncol=2, frameon=False, fontsize=8.8)
    fig.text(.53, .043, 'Transaction costs of 0.03% per side are included.', ha='center', fontsize=9)
    fig.text(.53, .022, 'Top: post-hoc strategy and buy-and-hold benchmarks. Frozen champion remains #478.', ha='center', fontsize=8.5)
    save(fig, 'combined_annual_return')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
