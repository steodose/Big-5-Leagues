"""Goals-based team ratings.

Each team's attack and defense strength come from its actual goals scored and
conceded this season, converted to a per-game rate and regressed toward the
league average by `REGRESSION_GAMES` pseudo-games so a small sample (or a hot
finishing run) doesn't dominate:

    attack_rate_i  = (GF_i + K·μ) / (GP_i + K)
    defense_rate_i = (GA_i + K·μ) / (GP_i + K)

where μ is the league mean goals per team-game and K = REGRESSION_GAMES. The
strength ratios (rate / μ) feed the match model; a team with no games played
regresses fully to average.

This follows the goals-for / goals-against methodology of the original R sims,
adding regression to the mean (and, in the match model, an explicit home edge).
"""
from __future__ import annotations

import numpy as np

from . import config


def compute(teams: list[dict]) -> dict:
    """Return {mu, att, def_, n}: att/def_ are length-N strength ratios (1 = avg)
    indexed by team position in `teams`."""
    n = len(teams)
    gf = np.array([t.get("goals_for") or 0.0 for t in teams], dtype=float)
    ga = np.array([t.get("goals_against") or 0.0 for t in teams], dtype=float)
    gp = np.array([t.get("games_played") or 0 for t in teams], dtype=float)

    total_gp = gp.sum()
    mu = float(gf.sum() / total_gp) if total_gp > 0 else config.DEFAULT_MU

    k = config.REGRESSION_GAMES
    att_rate = (gf + k * mu) / (gp + k)
    def_rate = (ga + k * mu) / (gp + k)

    return {"mu": mu, "att": att_rate / mu, "def_": def_rate / mu, "n": n}
