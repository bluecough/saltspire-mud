"""
Weather system for Saltspire MUD.

Weather transitions every 25-45 real minutes, with condition probabilities
weighted by the current in-game season. Weather changes are broadcast to all
connected players as a system message.
"""
from __future__ import annotations
import random as _random
import time as _time

# (key, room_description, change_announcement, weights[spring, summer, autumn, winter])
_TABLE = [
    ("clear",
     "The skies are clear.",
     "The clouds part. The skies clear.",
     [3, 5, 2, 2]),
    ("partly_cloudy",
     "Patches of cloud drift across a mostly clear sky.",
     "Clouds drift in, breaking up the sky.",
     [3, 3, 3, 2]),
    ("overcast",
     "The sky is a flat, featureless grey.",
     "The sky turns grey and overcast.",
     [2, 1, 4, 4]),
    ("windy",
     "A stiff wind cuts through the air.",
     "The wind picks up, gusting sharply.",
     [2, 1, 3, 3]),
    ("foggy",
     "A thick fog has settled in, cutting visibility to a few yards.",
     "Fog rolls in off the water and thickens.",
     [2, 1, 3, 2]),
    ("drizzle",
     "A fine drizzle drifts through the air.",
     "A light drizzle begins to fall.",
     [3, 1, 3, 2]),
    ("rain",
     "Rain falls in a steady grey curtain.",
     "The drizzle thickens into steady rain.",
     [2, 1, 3, 2]),
    ("heavy_rain",
     "Heavy rain lashes down.",
     "The rain intensifies to a heavy downpour.",
     [1, 1, 2, 2]),
    ("thunderstorm",
     "A thunderstorm rages overhead, lightning splitting the sky between crashes of thunder.",
     "Thunder rumbles in the distance. A storm closes overhead.",
     [1, 2, 1, 1]),
    ("windy_overcast",
     "Dark clouds race across the sky on a biting wind.",
     "Dark clouds pile in on a rising wind.",
     [1, 1, 2, 2]),
]

_SEASONS  = ("Spring", "Summer", "Autumn", "Winter")
_KEYS     = [r[0] for r in _TABLE]
_DESC     = {r[0]: r[1] for r in _TABLE}
_ANNOUNCE = {r[0]: r[2] for r in _TABLE}
_WEIGHTS  = {r[0]: r[3] for r in _TABLE}

_CHANGE_MIN = 1500   # 25 real minutes minimum between changes
_CHANGE_MAX = 2700   # 45 real minutes maximum


def _pick(season: str) -> str:
    idx = _SEASONS.index(season) if season in _SEASONS else 0
    weights = [_WEIGHTS[k][idx] for k in _KEYS]
    return _random.choices(_KEYS, weights=weights, k=1)[0]


class WeatherState:
    """Holds the current weather condition and handles timed transitions."""

    def __init__(self, season: str = "Spring"):
        self._key  = _pick(season)
        self._next = _time.time() + _random.randint(_CHANGE_MIN, _CHANGE_MAX)

    def maybe_update(self, now: float, season: str) -> str | None:
        """
        Call every engine tick. Returns a broadcast-ready announcement string
        if the weather just changed, or None if it didn't.
        """
        if now < self._next:
            return None
        self._next = now + _random.randint(_CHANGE_MIN, _CHANGE_MAX)
        new_key = _pick(season)
        if new_key == self._key:
            return None
        self._key = new_key
        return _ANNOUNCE[self._key]

    @property
    def description(self) -> str:
        """One-line current-weather description for room headers."""
        return _DESC.get(self._key, "The skies are clear.")
