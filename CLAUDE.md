# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A live standings + forecast dashboard for the Big 5 European leagues (Premier
League, La Liga, Bundesliga, Serie A, Ligue 1). Python pulls each league's table
and schedule from ESPN, runs a Monte-Carlo rest-of-season simulation, and writes
`site/data.json`; the static `site/` renders it with a league dropdown and two
tabs (Standings, Simulations). Modeled on the sibling `MLS` project
(dependency-free static site, Python pipeline, GitHub Pages). No xG yet (see
Roadmap). **No R.**

## Environment & commands

Python with `requests` + `numpy` (see `requirements.txt`). Use a venv.

```bash
python run.py                    # fetch -> build -> simulate -> write site/data.json
python run.py --season 2026      # override season (ESPN start-year: 2026 = 2026/27)
python run.py --as-of 2026-03-01 # backtest: rebuild table + forecast from a past date
python -m fetch.espn             # standalone: print all five league tables
cd site && python -m http.server 8000   # preview (page fetch()es data.json)
```

No test suite or linter. `fetch/espn.py` has a `__main__` block for ad-hoc checks.

## Pipeline / data flow

`run.py` is the single entry point. For each league in `fetch.leagues.LEAGUES`:

`fetch.espn.fetch_standings` + one `fetch.espn.fetch_team_matches` per team →
`build.standings.build_league` (order + PPG + zone) → `fetch.schedule`
`remaining_fixtures` (from the team match lists) → `sim.simulate.run` (odds
merged onto each team) → `build.export.write` → `site/data.json` (+ `data.js`) →
`site/app.js`.

## Module responsibilities

- `fetch/leagues.py` — the 5 leagues (key, name, country, ESPN slug, league-crest
  URL) and `default_season()` (European seasons are start-year labeled and kick
  off in August, so before August the current season is `year - 1`).
- `fetch/espn.py` — ESPN hidden API. Per-league single-table standings (points,
  W-L-D, goals, goal diff, ESPN `rank`, and the qualification/relegation `note` +
  its color) plus club logos/colors from the `/teams` endpoint. Note ESPN
  expresses goals as "points": `pointsFor/Against` are **goals**,
  `pointDifferential` is **goal** differential. `fetch_team_form` adds each
  club's last 6 league results via the per-team `/schedule` endpoint (one
  request per team, ~100 total; failures degrade to an empty form list).
- `build/standings.py` — orders each league by ESPN `rank` (falls back to
  points→GD→GF), derives `position` + `ppg`, and classifies each row's `zone`
  from the ESPN note text (`_ZONE_RULES` → ucl/uel/uecl/releg_playoff/releg).
  `ZONE_META` gives each zone its legend label + theme-safe accent color.
- `fetch/schedule.py` — `remaining_fixtures(teams, matches_by_id, as_of)` derives
  every unplayed fixture from the per-team match lists. Big 5 are pure double
  round-robins, so taking each team's *home* matches yields the full list once
  (no de-dup). `as_of` treats matches on/after a date as remaining (backtest).
- `sim/` — goals-based Monte-Carlo. `config.py` (N_SIMS=10000, REGRESSION_GAMES,
  HOME/AWAY_MULT), `ratings.py` (GF/GA per game regressed to league μ by
  REGRESSION_GAMES pseudo-games → attack/defense strength ratios), `simulate.py`
  (vectorized `(n_sims, n_teams)` Poisson Monte-Carlo: seeds each team with its
  current tally, plays out `remaining`, ranks the table by points→GD→GF every sim
  → title / top-4 (UCL) / European / relegation odds + projected pts/GD/finish).
  No per-sim Python loop.
- `build/standings.py` also has `spots_for` (per-league band sizes, default
  {ucl:4, europe:6, releg:3}) and `recompute_from_matches` (backtest: rebuild a
  row's stats from matches before `as_of`).
- `build/export.py` — writes `site/data.json` and `site/data.js`
  (`window.BIG5_DATA = …`, the `file://` fallback). Payload is
  `{meta, leagues: [{key, name, country, logo, zones, sim, teams}]}`; each team
  carries the sim outputs (`proj_points`, `p_title`, `p_ucl`, `p_europe`,
  `p_releg`, …).
- `site/` — plain HTML/CSS/vanilla JS. Two tabs (Standings, Simulations), each
  with a `<select>` dropdown that stays in sync (also hash-routed:
  `#epl`/`#laliga`/`#bundesliga`/`#seriea`/`#ligue1`). `renderTable` (zone band +
  amber points heat + form pills) and `renderSim` (probability heat cells), PNG
  (html2canvas) + CSV export per tab.

## Key facts (non-obvious)

- **ESPN `rank` is authoritative order.** It already applies each league's
  official tiebreakers (which differ by league — head-to-head in La Liga/Serie A,
  GD in the others) and any points deductions. The computed points→GD→GF key is
  only a fallback if a rank is ever missing.
- **Zones are data-driven, not hard-coded.** Exactly which places get Champions
  League / Europa / Conference / relegation varies by country and by season
  (coefficients, cup winners, league reshuffles), so `build/standings.py` reads
  ESPN's own per-row note text instead of assuming "top 4 = UCL". A zone the note
  doesn't mention simply doesn't appear in that league's legend.
- **Theme reuses the MLS identity** (black header + blue analytics accent,
  theme-aware light/dark). No xGD heat cell here (no xG yet).
- **Frontend is dependency-free** and must be served over http (it `fetch()`es
  `data.json`; `data.js` is the `file://` fallback).

## Key sim facts (non-obvious)

- **Regression to the mean is the main calibration knob.** `REGRESSION_GAMES`
  pseudo-games of league-average prior keep an early table from producing
  overconfident odds; it's the biggest improvement over the raw goals-for/against
  R model this is based on.
- **The sim conditions on results.** Each team is seeded with its current
  points/GF/GA and only the *remaining* fixtures are played out.
- **Off-season is a degenerate-but-correct case.** When the season is complete
  there are 0 remaining fixtures, so projected = actual and odds are 0/100. The
  frontend detects `sim.n_remaining == 0` and shows a "season complete" note.
  Use `--as-of` to forecast a past season mid-way (also how the tab was
  developed/verified).
- **Band sizes are config, not zones.** Title/UCL/Europe/relegation cutoffs come
  from `spots_for` (positional top/bottom-N), not ESPN's note text, which
  occasionally tags an out-of-position club that won a European trophy.

## Roadmap (architecture leaves room)

- **Expected goals (xG/xGD)** columns and xG-based ratings. Deferred
  deliberately: the free Big 5 xG sources (Understat, FBref, Fotmob) have all
  recently locked down against the kind of server-side fetch a GitHub Action
  does, so a reliable feed needs vetting before it goes in the scheduled pipeline.
