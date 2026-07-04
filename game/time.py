"""
Game time for Saltspire MUD.

Scale: 1 real second = 12 game seconds  (1 real hour = 12 game hours).
  1 game minute  =   5 real seconds
  1 game hour    =   5 real minutes
  1 game day     =   2 real hours
  1 game season  =  60 real hours  (30 game days)
  1 game year    =  10 real days   (120 game days, 4 seasons x 30)

Moon cycle = 28 game days (~56 real hours / ~2.3 real days)
"""
from __future__ import annotations
import time as _time

GAME_SCALE  = 12    # game seconds per real second
SEASON_DAYS = 30    # game days per season
YEAR_DAYS   = 120   # 4 x 30
MOON_CYCLE  = 28    # game days per lunar cycle

SEASONS = ("Spring", "Summer", "Autumn", "Winter")

# (day_lo, day_hi inclusive, label)
_MOON_TABLE = (
    ( 0,  0, "New Moon"),
    ( 1,  6, "Waxing Crescent"),
    ( 7,  7, "First Quarter"),
    ( 8, 13, "Waxing Gibbous"),
    (14, 14, "Full Moon"),
    (15, 20, "Waning Gibbous"),
    (21, 21, "Third Quarter"),
    (22, 27, "Waning Crescent"),
)


class GameTime:
    """Immutable snapshot of the current in-game time."""
    __slots__ = ("hour", "minute", "day_of_year", "season", "season_day", "moon_phase")

    def __init__(self, real_ts: float | None = None):
        gs               = int((_time.time() if real_ts is None else real_ts) * GAME_SCALE)
        self.minute      = (gs // 60) % 60
        self.hour        = (gs // 3600) % 24
        day_abs          = gs // 86400
        self.day_of_year = day_abs % YEAR_DAYS
        season_idx       = self.day_of_year // SEASON_DAYS
        self.season      = SEASONS[season_idx]
        self.season_day  = (self.day_of_year % SEASON_DAYS) + 1   # 1-indexed
        moon_day         = day_abs % MOON_CYCLE
        self.moon_phase  = next(
            name for lo, hi, name in _MOON_TABLE if lo <= moon_day <= hi
        )

    @property
    def time_of_day(self) -> str:
        h = self.hour
        if h == 0:    return "Midnight"
        if h <= 4:    return "Deep Night"
        if h == 5:    return "Before Dawn"
        if h == 6:    return "Sunrise"
        if h <= 11:   return "Morning"
        if h == 12:   return "High Noon"
        if h <= 16:   return "Afternoon"
        if h == 17:   return "Late Afternoon"
        if h == 18:   return "Dusk"
        if h == 19:   return "Sunset"
        if h <= 22:   return "Evening"
        return "Late Night"

    @property
    def is_day(self) -> bool:
        return 6 <= self.hour < 20

    @property
    def sky_desc(self) -> str:
        """Short atmospheric sentence about the current sky."""
        h = self.hour
        if h == 6:    return "The sun is cresting the eastern horizon."
        if h <= 11:   return "Morning light slants warmly across the land."
        if h == 12:   return "The sun stands at its zenith, casting short shadows."
        if h <= 16:   return "Afternoon sun hangs warm in a pale sky."
        if h == 17:   return "Long shadows reach east as the sun descends."
        if h == 18:   return "The sky is stained amber and crimson at the horizon."
        if h == 19:   return "Last light drains from the sky as the sun sets."
        if h <= 22:   return "Stars emerge one by one in the deepening dark."
        if h == 0:    return "The moon holds dominion over a silent world."
        if h <= 4:    return "The night is deep and still."
        return "The eastern sky brightens imperceptibly toward dawn."

    def summary(self) -> str:
        """Single-line time stamp for room display.
        e.g. 'Summer, Day 4 — Morning — Waxing Gibbous'"""
        return f"{self.season}, Day {self.season_day} — {self.time_of_day} — {self.moon_phase}"


def now() -> GameTime:
    """Return a fresh GameTime snapshot."""
    return GameTime()
