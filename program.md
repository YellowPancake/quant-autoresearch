# Quant-AutoResearch: instructions for the Agent

Read README.md, config/research.json, config/reward.py, strategy/strategy.py before starting.
The researcher prepares and seals the dataset and policy beforehand.
The sole protocol is config/time.json. Read its actual dates; the default example
uses train 2010–2019, validation 2020–2022 and test 2023–2026-09-11.
Only validation drives selection.
Earlier history may warm up indicators; labels may never cross partition ends.

## Scope

- Edit only strategy/strategy.py. Do not modify data, manifests, evaluator, runner, policy,
  instructions, archived attempts, or configuration. Do not install dependencies.
- Keep the candidate self-contained; do not add helper modules outside the single-file snapshot.
- Use Python's standard library and the frozen core.indicators library.
  Import indicators with `from core.indicators import sma, macd, boll, rsi`.
  Indicators return aligned series with None during warmup; never replace None with zero.
  Default MACD needs at least 34 bars for DEA/hist; check config/time.json for available history.
  Ask the researcher for a new data version if longer history is needed.
- Do not locate or read the held-out dataset or external full source data. Do not read validation labels through
  files or introspection. Do not call core.evaluate directly: all attempts use run.py.
- fit(train) may learn from training labels. allocate(observations, state) sees
  current and past prices only. No external I/O inside candidate strategy code.
- The deployment owner must enforce filesystem/network isolation where needed;
  these instructions and hash checks alone are not security controls.

## Loop

1. Establish the unchanged baseline: python3 run.py --description baseline.
2. Read the structured result and, for crashes, the attempt's log.txt.
3. Propose one testable change motivated by the research direction and evidence.
4. Modify strategy/strategy.py (factors, fitting logic, allocation rules).
5. Execute python3 run.py --description "hypothesis and change".
6. The runner records every attempt, keeps feasible improvements, and restores
   the champion after failures or discarded changes. Target satisfaction takes
   precedence over reward when choosing a feasible champion.
7. Continue without asking after every attempt, within the configured budget.
8. When validation target is reached or experiment budget is exhausted, execute
   python3 run.py --freeze if a feasible champion exists. Otherwise report failure.
   A total_seconds budget starts at the first attempt and includes thinking, search,
   pauses and evaluation. Check runs/session.json before work and stop at deadline.
9. Stop. Final testing belongs to the researcher; never iterate on test feedback.

Do not claim a target is guaranteed to be achievable. A crash consumes an attempt.
The runner caps evaluation wall time, not the external agent's thought/API cost.
The human must set spending/token limits in their coding-agent client separately.

## Optional literature search

Use web search through the host Agent only if provided/authorized by the
researcher. Record source URLs, publication dates, and the resulting hypothesis in
the experiment description. Do not search for held-out-period winners or outcomes.
Historical date filters cannot remove the LLM's pretrained future knowledge.
The minimal runner does not contain an API client, web connector, or memory DB.
