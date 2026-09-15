"""Researcher-owned policy. Edit BEFORE preparation; higher reward is better.

This is an executable example, not a recommended universal financial objective.
No eval() of config expressions, no LLM judge, no hidden reward shaping.
"""


def reward(metrics):
    return metrics["sharpe"]


def constraints(metrics, config):
    rules = config["constraints"]
    return (metrics["max_drawdown"] <= rules["max_drawdown"]
            and metrics["days"] >= rules["min_days"])


def target(metrics, score, config):
    return score >= config["target"]["reward_at_least"]
