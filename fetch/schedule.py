"""Derive a league's remaining fixtures from the per-team match lists.

The Big 5 are pure double round-robins, so every fixture has exactly one home
team. Taking each team's *home* matches therefore yields the full fixture list
once, with no de-duplication needed. `fetch.espn.fetch_team_matches` already
pulls each team's schedule (for the Form column), so this adds no requests.
"""
from __future__ import annotations


def remaining_fixtures(teams: list[dict], matches_by_id: dict[str, list[dict]],
                       as_of: str | None = None) -> list[dict]:
    """Return [{home, away}] (abbreviations) for every unplayed fixture.

    Normally "unplayed" = not completed. In backtest mode (`as_of` = YYYY-MM-DD)
    a fixture counts as remaining if it kicks off on/after that date, so a past
    season can be re-forecast from any point.
    """
    out: list[dict] = []
    for t in teams:
        for m in matches_by_id.get(t["espn_id"], []):
            if not m["is_home"]:
                continue
            is_future = (m["date"] >= as_of) if as_of else (not m["completed"])
            if is_future:
                out.append({"home": t["abbrev"], "away": m["opp"]})
    return out
