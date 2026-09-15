"""Fixed experiment budget, including elapsed time between agent attempts."""
import math
import time
from core.prepare import dump


def validate_budget(budget):
    count = budget.get('max_experiments')
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count <= 0):
        raise ValueError('max_experiments must be a positive integer or null')
    for name in ('seconds_per_experiment', 'total_seconds'):
        value = budget.get(name)
        if name == 'total_seconds' and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(name + ' must be finite and positive')
    if count is None and budget.get('total_seconds') is None:
        raise ValueError('Set either a total time budget or an experiment count')


def attempt_timeout(budget, runs, attempts, now=None):
    validate_budget(budget)
    now = time.time() if now is None else now
    limit = budget.get('max_experiments')
    if limit is not None and attempts >= limit:
        raise ValueError('Experiment budget exhausted; freeze the champion or report failure')
    duration = budget.get('total_seconds')
    timeout = budget['seconds_per_experiment']
    if duration is not None:
        import json
        path = runs / 'session.json'
        if path.exists():
            session = json.loads(path.read_text())
            if session['deadline_at'] - session['started_at'] != duration:
                raise ValueError('Session deadline does not match frozen budget')
            if now < session['started_at']:
                raise ValueError('System clock moved before session start')
        else:
            if attempts:
                raise ValueError('Missing session clock for existing experiments')
            session = {'started_at': now, 'deadline_at': now + duration, 'total_seconds': duration}
            dump(path, session)
        remaining = session['deadline_at'] - now
        if remaining <= 0:
            raise ValueError('Research time budget exhausted; freeze the champion or report failure')
        timeout = min(timeout, remaining)
    return timeout
