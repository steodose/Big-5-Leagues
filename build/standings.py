"""Order each league table and derive the per-row fields the site renders.

ESPN's `rank` already applies each league's official tiebreakers (and any
points deductions), so we trust it for ordering and fall back to a generic
points -> goal-difference -> goals-for key only if a rank is ever missing.

Each row also carries a `zone`: a normalized qualification / relegation band
derived from ESPN's own note text + color, so the frontend can draw colored
edges and a legend without hard-coding which places qualify in which league
(those vary — and change season to season).
"""
from __future__ import annotations

# Normalize ESPN's free-text notes into a small set of stable zone slugs. The
# first substring that matches (case-insensitive) wins; order matters so that
# "Champions League qualifying" is caught before a bare "qualifying".
_ZONE_RULES = [
    ("champions league", "ucl"),
    ("europa league", "uel"),
    ("conference league", "uecl"),
    ("relegation playoff", "releg_playoff"),
    ("relegation", "releg"),
]

# Display label + accent color per zone. Colors are chosen to read in both
# light and dark themes (ESPN's own note colors are pale and wash out on dark).
ZONE_META = {
    "ucl":           {"label": "Champions League", "color": "#2f6fed"},
    "uel":           {"label": "Europa League",     "color": "#e08e00"},
    "uecl":          {"label": "Conference League", "color": "#12a150"},
    "releg_playoff": {"label": "Relegation playoff", "color": "#e0653a"},
    "releg":         {"label": "Relegation",         "color": "#e34948"},
}


def _classify_zone(note: str | None) -> str | None:
    if not note:
        return None
    low = note.lower()
    for needle, slug in _ZONE_RULES:
        if needle in low:
            return slug
    return None


def _tiebreak_key(t: dict) -> tuple:
    """Generic fallback ordering (higher is better): points, GD, GF."""
    return (t.get("points") or 0, t.get("goal_diff") or 0, t.get("goals_for") or 0)


def _sorted_rows(rows: list[dict]) -> list[dict]:
    if rows and all(t.get("rank") is not None for t in rows):
        return sorted(rows, key=lambda t: t["rank"])
    return sorted(rows, key=_tiebreak_key, reverse=True)


# How many places each band covers, per league. Kept explicit (rather than read
# from ESPN's zone notes) because those vary season to season and occasionally
# tag an out-of-position club that won a European competition. Bottom-3 is the
# common "relegation-threatened" band across the Big 5 (Germany & France drop 2
# automatically plus a play-off in 16th/18th).
DEFAULT_SPOTS = {"ucl": 4, "europe": 6, "releg": 3}


def spots_for(teams: list[dict], override: dict | None = None) -> dict:
    """Clamp the {ucl, europe, releg} band sizes to a sane range for N teams."""
    s = dict(override or DEFAULT_SPOTS)
    n = len(teams)
    s["ucl"] = min(max(s.get("ucl", 4), 1), n)
    s["europe"] = min(max(s.get("europe", 6), s["ucl"]), n)
    s["releg"] = min(max(s.get("releg", 3), 1), n - 1)
    return s


def recompute_from_matches(rows: list[dict], matches_by_id: dict[str, list[dict]],
                           as_of: str | None) -> None:
    """Backtest helper: overwrite each row's stats from matches before `as_of`
    (in place), so a past season's table can be rebuilt at an earlier date.
    Clears ESPN `rank` so ordering falls back to the points→GD→GF key."""
    for t in rows:
        played = [m for m in matches_by_id.get(t["espn_id"], [])
                  if m["completed"] and m["gf"] is not None and m["ga"] is not None
                  and (as_of is None or m["date"] < as_of)]
        w = sum(1 for m in played if m["gf"] > m["ga"])
        l = sum(1 for m in played if m["gf"] < m["ga"])
        d = len(played) - w - l
        gf = sum(m["gf"] for m in played)
        ga = sum(m["ga"] for m in played)
        t.update(games_played=len(played), wins=w, draws=d, losses=l,
                 goals_for=gf, goals_against=ga, goal_diff=gf - ga,
                 points=3 * w + d, rank=None)


def build_league(rows: list[dict]) -> dict:
    """Order one league and derive PPG, position, and zone for each row.

    Returns {teams, zones} where `zones` is the ordered list of distinct zones
    present in this table (for the legend).
    """
    teams = _sorted_rows(rows)
    seen: list[str] = []
    for i, t in enumerate(teams, start=1):
        gp = t.get("games_played") or 0
        t["position"] = i
        t["ppg"] = round(t["points"] / gp, 2) if gp else 0.0
        t["zone"] = _classify_zone(t.get("note"))
        if t["zone"] and t["zone"] not in seen:
            seen.append(t["zone"])
    zones = [{"key": z, **ZONE_META[z]} for z in seen if z in ZONE_META]
    return {"teams": teams, "zones": zones}
