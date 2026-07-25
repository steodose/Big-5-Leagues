# Big 5 Leagues — Standings

A live standings dashboard for Europe's five biggest leagues — the
**Premier League**, **La Liga**, **Bundesliga**, **Serie A**, and **Ligue 1** —
in one clean, sortable table per competition, with the European and relegation
places marked exactly as each league draws them.

A companion to the [MLS Standings](https://github.com/steodose) dashboard,
styled to match, and a modern rebuild of the original
[Big 5 Leagues R/Shiny dashboard](https://steodosescu.shinyapps.io/Big-5-Leagues/).
A **Between the Pipes** project.

## What it shows

- **One table per league** — pick a league from the dropdown. GP, W-D-L, points
  (amber heatmap), **PPG**, GF / GA / GD, and a **Form** guide of each club's
  last six results (blue win / grey draw / red loss). Sortable on any column.
- **Qualification & relegation bands** — a colored edge marks each club's zone:
  Champions League, Europa League, Conference League, and relegation (plus the
  relegation play-off where a league has one). Which places qualify differs by
  country and shifts season to season, so the bands are read straight from the
  live table rather than hard-coded.
- **Simulations** — a Monte-Carlo rest-of-season forecast per league. Team
  strength comes from goals scored and conceded (regressed toward the league
  average, with a home-field edge); every remaining fixture is played out
  thousands of times to give each club's odds of winning the **title**, a
  **top-four** or **European** finish, or **relegation**, plus projected points,
  goal difference, and average finishing position.
- Per-league **PNG** and **CSV** export on both tabs.

## Data source (no API keys required)

- **[ESPN](https://www.espn.com/soccer/)** hidden API — live standings, records,
  goals, club logos, qualification / relegation notes, and each club's schedule
  (used for the Form guide and to reconstruct remaining fixtures for the sim).

The season follows ESPN's start-year convention (2025 = the 2025/26 season) and
`fetch.leagues.default_season` rolls to the new season automatically each August.

## Stack

Dependency-free static site. Python (only `requests`) pulls the data and writes
`site/data.json`; `site/` is plain HTML/CSS/vanilla JS — no framework, no build
step. Deployed to GitHub Pages; a scheduled GitHub Action refreshes the data.

## Update workflow

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python run.py                    # fetch -> build -> simulate -> write site/data.json
python run.py --season 2026      # override the season (2026 = 2026/27)
python run.py --as-of 2026-03-01 # backtest: rebuild the table + forecast from a past date

# preview (must be served over http — the page fetch()es data.json)
cd site && python -m http.server 8000   # -> http://localhost:8000
```

The GitHub Action (`.github/workflows/pages.yml`) regenerates the data and
redeploys **Friday, Saturday, Sunday & Monday at ~3pm US Pacific** (22:30 UTC),
after the weekend's matches. Data is generated fresh at deploy time and not
committed back, so the live site stays current with no commit noise. Trigger it
by hand anytime from the Actions tab ("Run workflow").

## Verify the fetcher standalone

```bash
python -m fetch.espn      # prints all five league tables
```

## Off-season note

The forecast conditions on games played, so during the summer break (when the
just-finished season shows zero remaining fixtures) the Simulations tab shows the
final table with settled odds and says so. It comes alive automatically once the
new season kicks off and fixtures remain to be played. To see it mid-season now,
use `--as-of` with a date inside a past season.

## Roadmap

- **Expected goals (xG / xGD)** columns and xG-based ratings, once a Big 5 xG
  feed that survives an automated fetch is wired in (the classic free sources —
  Understat, FBref, Fotmob — have all recently locked down against server-side
  scraping).

---

Data: [ESPN](https://www.espn.com/soccer/) ·
by [Stephan Teodosescu](https://stephanteodosescu.com)
