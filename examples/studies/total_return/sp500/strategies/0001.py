"""Unchanged buy-and-hold baseline for the first measured attempt."""
def fit(train):
    return None

def allocate(observations, state):
    return {r['symbol']: 1.0 / len(observations) for r in observations}
