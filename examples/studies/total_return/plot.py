"""Render all unified reevaluations with the same chart style and NAV origin."""
import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from evaluate import HERE, read_csv

NAMES = {'csi300': 'CSI 300', 'sp500': 'S&P 500', 'broad_market': 'Broad-Market Indices'}


def plot(market):
    root = HERE / market
    output = root / 'figures'
    output.mkdir(exist_ok=True)
    report = json.loads((root / 'results.json').read_text())
    curves = defaultdict(list)
    for r in read_csv(root / 'equity.csv'):
        if r['partition'] == 'test':
            curves[r['attempt']].append((date.fromisoformat(r['date']), float(r['equity'])))
    selected, frozen = report['posthoc_attempt'], report['frozen_attempt']
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 10, 'axes.labelsize': 10,
        'xtick.labelsize': 9, 'ytick.labelsize': 9, 'axes.linewidth': .8, 'axes.edgecolor': '#222222',
        'text.color': '#222222', 'axes.labelcolor': '#222222', 'xtick.color': '#222222',
        'ytick.color': '#222222', 'xtick.direction': 'in', 'ytick.direction': 'in',
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'savefig.facecolor': 'white'})
    def grid(ax):
        ax.grid(True, color='#DADADA', linestyle=':', linewidth=.55)
        ax.set_axisbelow(True)
        ax.tick_params(top=True, right=True)
    def equity(ax):
        lines = [(selected, f'Strategy #{int(selected)} (post hoc)', '#D95F02')]
        if market == 'sp500' and curves[selected] == curves['baseline_sp500']:
            # The initial buy-and-hold candidate wins; do not draw a fake second path.
            lines = [(selected, f'#{int(selected)} / SPY buy-and-hold (same path)', '#1F77B4'),
                     (frozen, f'Frozen strategy #{int(frozen)} (SPY proxy)', '#D95F02')]
        elif market == 'broad_market':
            lines += [('baseline_growth', 'ChiNext ETF buy-and-hold (dividends reinvested)', '#2CA02C'),
                      ('baseline_csi300', 'CSI 300 TR buy-and-hold', '#1F77B4')]
        else:
            label = 'SPY buy-and-hold (dividends reinvested)' if market == 'sp500' else NAMES[market] + ' TR buy-and-hold'
            lines += [('baseline_' + market, label, '#1F77B4')]
        for key, label, color in lines:
            dates, nav = zip(*curves[key])
            assert nav[0] == 1
            ax.plot(dates, nav, lw=1.5, color=color, label=label)
        grid(ax)
        ax.set_xlim(dates[0], dates[-1])
        ax.set_xlabel('Date')
        ax.set_ylabel('Net asset value (initial = 1)')
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    def save(fig, name):
        for ext in ('png', 'pdf', 'svg'):
            path = output / (name + '.' + ext)
            fig.savefig(path, dpi=240)
            if ext == 'svg':
                path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
        plt.close(fig)
    caption = 'Total return; next-close execution; transaction costs of 0.03% per side.'
    selection = f'Post-hoc test comparison of {report["milestone_count"]} fixed milestones; frozen champion remains #{int(frozen)}.'
    fig, ax = plt.subplots(figsize=(10.8, 5.7))
    fig.subplots_adjust(left=.09, right=.975, bottom=.29, top=.87)
    title = NAMES[market] + (' (SPY proxy)' if market == 'sp500' else '')
    fig.suptitle(title + ': Test-Period Equity Curves', y=.97, fontsize=15)
    equity(ax)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='center', bbox_to_anchor=(.5, .135), ncol=2,
               frameon=False, fontsize=8.5)
    fig.text(.5, .065, caption, ha='center', fontsize=9)
    fig.text(.5, .025, selection, ha='center', fontsize=8.5)
    save(fig, 'test_equity')
    attempts = list(report['results'])
    for metric, name in [('annual_return', 'combined_annual'), ('total_return', 'combined_returns')]:
        fig, axes = plt.subplots(3, 1, figsize=(10.8, 11.2), gridspec_kw={'height_ratios': [1.35, 1, 1]})
        fig.subplots_adjust(left=.09, right=.975, bottom=.125, top=.94, hspace=.52)
        fig.suptitle(title + ': Unified Total-Return Reevaluation', fontsize=15, y=.985)
        equity(axes[0])
        axes[0].legend(loc='upper center', bbox_to_anchor=(.5, -.2), ncol=2,
                       frameon=False, fontsize=8)
        for ax, key in [(axes[1], metric), (axes[2], 'max_drawdown')]:
            for partition, color, label in [('validation', '#D95F02', 'Validation'), ('test', '#1F77B4', 'Test')]:
                ax.plot(range(1, len(attempts) + 1), [report['results'][a][partition][key] for a in attempts],
                        marker='o', markersize=3, color=color, lw=1.2, label=label)
            ax.set_xticks(range(1, len(attempts) + 1), [str(int(a)) for a in attempts], rotation=45)
            ax.set_xlabel('Historical validation-champion attempt')
            ax.set_ylabel({'annual_return': 'CAGR', 'total_return': 'Cumulative return', 'max_drawdown': 'Maximum drawdown'}[key])
            ax.yaxis.set_major_formatter(PercentFormatter(1))
            grid(ax)
            ax.legend(frameon=False, fontsize=9)
        fig.text(.5, .039, caption, ha='center', fontsize=9)
        fig.text(.5, .019, selection, ha='center', fontsize=8.5)
        save(fig, name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', choices=list(NAMES), required=True)
    plot(parser.parse_args().market)
