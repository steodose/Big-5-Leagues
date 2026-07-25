"""Vectorized Monte-Carlo of a league's remaining season.

Seeds each team with its current table tally, plays every remaining fixture
`N_SIMS` times (independent Poisson goals from the goals-based match model plus a
home edge), then ranks the full table each sim to tally title / European /
relegation odds. Everything is a `(n_sims, n_teams)` array — no per-sim loop.

Tiebreak is points → goal difference → goals for (the common Big-5 order; a few
leagues use head-to-head first, which the sim approximates with GD/GF).
"""
from __future__ import annotations

import numpy as np

from . import config, ratings


def _match_lambdas(rt: dict, home_idx: np.ndarray, away_idx: np.ndarray):
    """Expected goals for each fixture from the strengths + home advantage."""
    mu, att, dfn = rt["mu"], rt["att"], rt["def_"]
    lam_home = mu * att[home_idx] * dfn[away_idx] * config.HOME_MULT
    lam_away = mu * att[away_idx] * dfn[home_idx] * config.AWAY_MULT
    return (np.clip(lam_home, config.MIN_LAMBDA, None),
            np.clip(lam_away, config.MIN_LAMBDA, None))


def _rank_key(pts, gd, gf):
    """Scalar sort key (higher = better): points → goal diff → goals for.
    Range-separated so no tier bleeds into the next (gd/gf offset off the floor)."""
    return pts * 1e8 + (gd + 1000.0) * 1e3 + gf


def _finish(key: np.ndarray) -> np.ndarray:
    """Given a (n_sims, N) rank key, return (n_sims, N) finishing places (1=1st)."""
    order = np.argsort(-key, axis=1)                 # team ids best→worst per sim
    place = np.empty_like(order)
    ranks = np.broadcast_to(np.arange(1, key.shape[1] + 1), order.shape)
    np.put_along_axis(place, order, ranks, axis=1)
    return place


def run(teams: list[dict], remaining: list[dict], spots: dict,
        n_sims: int | None = None) -> dict:
    """Return {meta, results}: per-team title/UCL/Europe/relegation odds, average
    finish, and projected points/GD. `remaining` is [{home, away}] abbreviations;
    `spots` is {ucl, europe, releg} — how many places each band covers."""
    n_sims = n_sims or config.N_SIMS
    n = len(teams)
    idx = {t["abbrev"]: i for i, t in enumerate(teams)}
    rng = np.random.default_rng(config.SEED)

    base_pts = np.array([t["points"] for t in teams], dtype=float)
    base_gf = np.array([t["goals_for"] for t in teams], dtype=float)
    base_ga = np.array([t["goals_against"] for t in teams], dtype=float)

    hi, ai = [], []
    for f in remaining:
        if f["home"] in idx and f["away"] in idx:
            hi.append(idx[f["home"]]); ai.append(idx[f["away"]])
    home_idx = np.array(hi, dtype=int); away_idx = np.array(ai, dtype=int)

    rt = ratings.compute(teams)

    pts = np.tile(base_pts, (n_sims, 1))
    gf = np.tile(base_gf, (n_sims, 1))
    ga = np.tile(base_ga, (n_sims, 1))

    if len(home_idx):
        lam_home, lam_away = _match_lambdas(rt, home_idx, away_idx)
        hg = rng.poisson(lam_home, size=(n_sims, len(home_idx))).astype(np.int16)
        ag = rng.poisson(lam_away, size=(n_sims, len(home_idx))).astype(np.int16)
        home_pts = np.where(hg > ag, 3, np.where(hg == ag, 1, 0)).astype(np.int16)
        away_pts = np.where(ag > hg, 3, np.where(hg == ag, 1, 0)).astype(np.int16)
        for t in range(n):
            hm = home_idx == t
            am = away_idx == t
            if hm.any():
                pts[:, t] += home_pts[:, hm].sum(1)
                gf[:, t] += hg[:, hm].sum(1); ga[:, t] += ag[:, hm].sum(1)
            if am.any():
                pts[:, t] += away_pts[:, am].sum(1)
                gf[:, t] += ag[:, am].sum(1); ga[:, t] += hg[:, am].sum(1)

    gd = gf - ga
    place = _finish(_rank_key(pts, gd, gf))

    ucl, europe, releg = spots["ucl"], spots["europe"], spots["releg"]
    p_title = (place == 1).mean(0)
    p_ucl = (place <= ucl).mean(0)
    p_europe = (place <= europe).mean(0)
    p_releg = (place > n - releg).mean(0)
    avg_finish = place.mean(0)
    proj_points = pts.mean(0)
    proj_gd = gd.mean(0)

    results = {}
    for i, t in enumerate(teams):
        results[t["abbrev"]] = {
            "proj_points": round(float(proj_points[i]), 1),
            "proj_gd": round(float(proj_gd[i]), 1),
            "avg_finish": round(float(avg_finish[i]), 1),
            "p_title": float(p_title[i]),
            "p_ucl": float(p_ucl[i]),
            "p_europe": float(p_europe[i]),
            "p_releg": float(p_releg[i]),
        }
    return {
        "meta": {"n_sims": n_sims, "league_mu": round(rt["mu"], 2),
                 "n_remaining": int(len(home_idx)), "spots": spots},
        "results": results,
    }
