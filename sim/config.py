"""Simulation tunables. Start here to recalibrate the forecast."""

# Monte-Carlo
N_SIMS = 10000
SEED = 1234

# Ratings: pseudo-games of league-average prior mixed into each team's goal
# rate. Higher = more regression to the mean (trusts the sample less). With a
# Big-5 spread in true goal rates of ~0.35-0.4/game against Poisson noise of
# ~1.2/game, a sample is half signal after ~10-12 games; 15 adds a margin since
# there's no preseason prior. (6 gave ~95% title odds a few weeks in.) This is
# the main calibration knob.
REGRESSION_GAMES = 15.0

# Home-field advantage as multiplicative goal factors (home ↑, away ↓). Tuned so
# two average teams produce ~1.50 vs ~1.20 goals — a realistic Big-5 home edge of
# ~0.30 goals at ~2.7 goals/game.
HOME_MULT = 1.11
AWAY_MULT = 0.89

# Keep expected goals off the floor.
MIN_LAMBDA = 0.15

# Fallback league mean goals per team-game before any matches are played.
DEFAULT_MU = 1.35
