#!/usr/bin/env python3
"""Single entry point: fetch -> build -> simulate -> write site/data.json (+ .js).

    python run.py                    # season currently in play (see leagues.default_season)
    python run.py --season 2026      # override (ESPN start-year: 2026 = 2026/27)
    python run.py --as-of 2026-03-01 # backtest: rebuild the table + forecast from a past date

Pulls live standings + each club's schedule from ESPN for the Big 5 European
leagues, orders every table, derives PPG / form / European & relegation zones,
runs a Monte-Carlo rest-of-season forecast per league, and writes the payload the
static site renders.
"""
from __future__ import annotations

import argparse

from fetch import espn, schedule
from fetch.leagues import LEAGUES, default_season
from build import standings, export
from sim import simulate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=default_season(),
                        help="ESPN start-year of the season (default: current)")
    parser.add_argument("--as-of", dest="as_of", default=None,
                        help="Backtest date YYYY-MM-DD: rebuild the table and "
                             "forecast the rest of the season from that point")
    args = parser.parse_args()

    label = f"{args.season}/{(args.season + 1) % 100:02d}"
    print(f"Building Big 5 for the {label} season"
          + (f" as of {args.as_of}" if args.as_of else "") + "…")

    out_leagues = []
    for lg in LEAGUES:
        rows = espn.fetch_standings(lg["espn_slug"], args.season)

        # One schedule request per team → form guide + remaining fixtures.
        matches_by_id = {
            t["espn_id"]: espn.fetch_team_matches(lg["espn_slug"], t["espn_id"], args.season)
            for t in rows
        }
        if args.as_of:
            standings.recompute_from_matches(rows, matches_by_id, args.as_of)
        for t in rows:
            t["form"] = espn.form_of(matches_by_id[t["espn_id"]], as_of=args.as_of)

        built = standings.build_league(rows)
        spots = standings.spots_for(built["teams"], lg.get("spots"))
        remaining = schedule.remaining_fixtures(built["teams"], matches_by_id, args.as_of)

        sim_out = simulate.run(built["teams"], remaining, spots)
        for t in built["teams"]:
            t.update(sim_out["results"][t["abbrev"]])

        print(f"  {lg['name']:<16} {len(built['teams']):>2} teams, "
              f"{len(built['zones'])} zones, {sim_out['meta']['n_remaining']:>3} fixtures to sim")
        out_leagues.append({**lg, **built, "sim": sim_out["meta"]})

    path = export.write(out_leagues, args.season, sources=["ESPN"],
                        sim_n=simulate.config.N_SIMS, as_of=args.as_of)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
