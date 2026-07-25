"""Simulation tunables. Start here to recalibrate the forecast."""

# Monte-Carlo
N_SIMS = 10000
SEED = 1234

# Ratings: pseudo-games of league-average prior mixed into each team's goal
# rate. Higher = more regression to the mean (trusts the sample less). ~6 games
# of prior keeps an early table honest without washing out real signal, and is
# the main calibration knob.
REGRESSION_GAMES = 6.0

# Home-field advantage as multiplicative goal factors (home ↑, away ↓). Tuned so
# two average teams produce ~1.50 vs ~1.20 goals — a realistic Big-5 home edge of
# ~0.30 goals at ~2.7 goals/game.
HOME_MULT = 1.11
AWAY_MULT = 0.89

# Keep expected goals off the floor.
MIN_LAMBDA = 0.15

# Fallback league mean goals per team-game before any matches are played.
DEFAULT_MU = 1.35
