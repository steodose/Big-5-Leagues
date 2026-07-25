"""The Big 5 European leagues, and the season-year convention.

Each league is keyed by a short slug the frontend uses in its URL hash and in
the league dropdown. `espn_slug` is the code ESPN's soccer API expects; `logo`
is ESPN's league crest (falls back gracefully in the UI if it ever 404s).
"""
from __future__ import annotations

import datetime

# Order here is the order of the dropdown (and default = first).
LEAGUES = [
    {"key": "epl",        "name": "Premier League", "country": "England",
     "espn_slug": "eng.1", "logo": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png"},
    {"key": "laliga",     "name": "La Liga",        "country": "Spain",
     "espn_slug": "esp.1", "logo": "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png"},
    {"key": "bundesliga", "name": "Bundesliga",     "country": "Germany",
     "espn_slug": "ger.1", "logo": "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png"},
    {"key": "seriea",     "name": "Serie A",        "country": "Italy",
     "espn_slug": "ita.1", "logo": "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png"},
    {"key": "ligue1",     "name": "Ligue 1",        "country": "France",
     "espn_slug": "fra.1", "logo": "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png"},
]


def default_season(today: datetime.date | None = None) -> int:
    """The season currently in play, by ESPN's start-year convention.

    European seasons span two calendar years and ESPN labels them by the *start*
    year (2025 = the 2025/26 season). They kick off in August, so before August
    the current season is still the one that started the previous year.
    """
    today = today or datetime.date.today()
    return today.year if today.month >= 8 else today.year - 1
