# Research CSI300, S&P 500, or your own instrument

Real histories are bundled under `data/csi300/` and `data/sp500/` in this repository. See [source information and redistribution status](../data/README.md).
Configure `config/` in the distribution repository before preparing each study.

```sh
python3 prepare.py --example csi300 --workspace ../csi300-study
python3 prepare.py --example sp500 --workspace ../sp500-study
```

Each command creates an independent workspace plus a sibling final-holdout directory.
The workspaces receive the strategy, configuration, engine and training/validation cache.
They do not receive the full source data. Start your Agent in the chosen workspace:

```sh
cd ../csi300-study
python3 run.py --description baseline
```

Ask the agent to follow `program.md`. After research, freeze the feasible champion
with `python3 run.py --freeze`. The researcher runs the final evaluation once using
the corresponding holdout directory.

## Other instruments

**Convert other data to the same format.** Required fields are `date,open,close` and
one identifier column, either `index_id` or `symbol`. The bundled 13-column format
preserves additional archive fields, but they are optional for the minimal evaluator.

```sh
python3 prepare.py --csv /path/to/your-prices.csv --workspace ../custom-study
cd ../custom-study
python3 run.py --description baseline
```

Validate dates against the instrument's market calendar and use consistent price units
and adjustment conventions. Multiple instruments in one study must share exactly the
same session dates. Use separate studies for markets with different calendars.

The default protocol uses 2010–2019 for training, 2020–2022 for validation and
2023–2026-09-11 for final testing. Change dates, history window, costs, reward, target
and budget before preparing if they do not fit your dataset or research question.

No strategy performance is published in this package. Synthetic prices remain only
for software testing; the user-facing examples use real index histories.
