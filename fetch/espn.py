"""Pull Big 5 league standings and club metadata from ESPN's public API.

No API key required. For each league two endpoints are used:

- standings: the single league table — points, W-L-D, goals for/against, goal
  differential, ESPN's own rank (which already applies each league's official
  tiebreakers and any points deductions), and a `note` describing European
  qualification / relegation, with the color ESPN paints that zone.
- teams: club primary/alternate colors and the 500px logo URL.

Run standalone to eyeball every league's parsed table:

    python -m fetch.espn
"""
from __future__ import annotations

import requests

STANDINGS_URL = "https://site.web.api.espn.com/apis/v2/sports/soccer/{slug}/standings"
TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams"
TIMEOUT = 30

# ESPN stat name -> the field we keep. ESPN expresses goals as "points" (soccer
# scoring), so pointsFor/Against are GOALS and pointDifferential is GOAL diff.
_STAT_MAP = {
    "gamesPlayed": "games_played",
    "wins": "wins",
    "losses": "losses",
    "ties": "draws",
    "points": "points",
    "pointsFor": "goals_for",
    "pointsAgainst": "goals_against",
    "pointDifferential": "goal_diff",
    "rank": "rank",
}


def _get(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, params=params, timeout=TIMEOUT,
                        headers={"User-Agent": "big5-dashboard/1.0"})
    resp.raise_for_status()
    return resp.json()


def fetch_team_meta(slug: str) -> dict[str, dict]:
    """Return {espn_id: {color, alt_color, logo}} for every club in a league."""
    out: dict[str, dict] = {}
    try:
        data = _get(TEAMS_URL.format(slug=slug))
    except requests.RequestException:
        return out  # colors are a nice-to-have; standings carry the logos too
    for league in data.get("sports", [])[0].get("leagues", []):
        for entry in league.get("teams", []):
            t = entry.get("team", {})
            logos = t.get("logos") or []
            out[t["id"]] = {
                "color": "#" + t["color"] if t.get("color") else None,
                "alt_color": "#" + t["alternateColor"] if t.get("alternateColor") else None,
                "logo": logos[0]["href"] if logos else None,
            }
    return out


def _parse_entry(entry: dict, meta: dict[str, dict]) -> dict:
    t = entry["team"]
    stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
    row: dict = {
        "espn_id": t["id"],
        "abbrev": t.get("abbreviation") or t["id"],
        "name": t.get("displayName", t.get("name")),
        "short_name": t.get("shortDisplayName"),
    }
    for espn_name, field in _STAT_MAP.items():
        val = stats.get(espn_name)
        row[field] = int(val) if val is not None else None
    # Qualification / relegation note (ESPN colors + describes each zone).
    note = entry.get("note") or {}
    row["note"] = note.get("description")
    row["note_color"] = note.get("color")
    # Team meta (logo taken from standings if present, else /teams).
    m = meta.get(t["id"], {})
    logos = t.get("logos") or []
    row["logo"] = (logos[0]["href"] if logos else None) or m.get("logo")
    row["color"] = m.get("color")
    row["alt_color"] = m.get("alt_color")
    return row


SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/teams/{tid}/schedule"
)


def _score(competitor: dict) -> int | None:
    sc = competitor.get("score")
    if isinstance(sc, dict):
        sc = sc.get("value")
    try:
        return int(float(sc))
    except (TypeError, ValueError):
        return None


def fetch_team_matches(slug: str, team_id: str, season: int) -> list[dict]:
    """Return every league match for a team (played and scheduled), oldest first.

    Each item: {"id", "date": iso, "is_home": bool, "opp": abbrev,
    "gf": int|None, "ga": int|None, "completed": bool} — enough to derive both the
    form guide and the league's remaining-fixture list. One request per team;
    failures degrade to an empty list so a single bad fetch never sinks the run.
    """
    try:
        data = _get(SCHEDULE_URL.format(slug=slug, tid=team_id), {"season": season})
    except requests.RequestException:
        return []

    out: list[dict] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        mine = opp = None
        for c in comp.get("competitors", []):
            if str(c.get("team", {}).get("id")) == str(team_id):
                mine = c
            else:
                opp = c
        if not mine or not opp:
            continue
        out.append({
            "id": ev.get("id"),
            "date": (ev.get("date") or "")[:10],
            "is_home": mine.get("homeAway") == "home",
            "opp": (opp.get("team", {}).get("abbreviation")
                    or opp.get("team", {}).get("shortDisplayName")),
            "gf": _score(mine),
            "ga": _score(opp),
            "completed": bool(comp.get("status", {}).get("type", {}).get("completed")),
        })
    out.sort(key=lambda m: m["date"])
    return out


def form_of(matches: list[dict], last: int = 6, as_of: str | None = None) -> list[dict]:
    """Reduce a team's matches to its most recent `last` results as pill dicts:
    {"r": "W"|"D"|"L", "o": opp, "s": "2-1", "h": home, "d": date}. `as_of`
    (YYYY-MM-DD) restricts to matches strictly before that date (backtest mode)."""
    pills: list[dict] = []
    for m in matches:
        if not m["completed"] or m["gf"] is None or m["ga"] is None:
            continue
        if as_of is not None and m["date"] >= as_of:
            continue
        r = "W" if m["gf"] > m["ga"] else ("L" if m["gf"] < m["ga"] else "D")
        pills.append({"r": r, "o": m["opp"], "s": f"{m['gf']}-{m['ga']}",
                      "h": m["is_home"], "d": m["date"]})
    return pills[-last:]


def fetch_team_form(slug: str, team_id: str, season: int, last: int = 6) -> list[dict]:
    """Convenience: fetch a team's matches and reduce to the form guide."""
    return form_of(fetch_team_matches(slug, team_id, season), last)


def fetch_standings(slug: str, season: int) -> list[dict]:
    """Return the league's ordered rows [{name, abbrev, ...stats}, ...]."""
    data = _get(STANDINGS_URL.format(slug=slug), {"season": season})
    meta = fetch_team_meta(slug)
    children = data.get("children")
    if children:
        entries = children[0].get("standings", {}).get("entries", [])
    else:
        entries = data.get("standings", {}).get("entries", [])
    return [_parse_entry(e, meta) for e in entries]


if __name__ == "__main__":
    from fetch.leagues import LEAGUES, default_season
    season = default_season()
    for lg in LEAGUES:
        rows = fetch_standings(lg["espn_slug"], season)
        print(f"\n=== {lg['name']} ({season}/{season + 1 - 2000}) ===")
        print(f"{'#':>2} {'TEAM':<26} {'GP':>3} {'W':>2} {'D':>2} {'L':>2} "
              f"{'PTS':>4} {'GF':>3} {'GA':>3} {'GD':>4}  NOTE")
        for t in rows:
            print(f"{t['rank']:>2} {t['name'][:26]:<26} {t['games_played']:>3} "
                  f"{t['wins']:>2} {t['draws']:>2} {t['losses']:>2} "
                  f"{t['points']:>4} {t['goals_for']:>3} {t['goals_against']:>3} "
                  f"{t['goal_diff']:>+4}  {t['note'] or ''}")
