"""Lunar and sky facts that the hand-rolled series in ``calc.py`` cannot know.

**Why this module exists next to a perfectly good series.** ``calc.py`` keeps a
truncated ELP2000 series for the Moon's geocentric ecliptic longitude. Measured
against Astronomy Engine over 2020-2030 (16072 samples every 6h) it stays within
0.43 degrees of the truth — comfortably inside a 30-degree zodiac sign. It is
therefore left exactly as it is. Two things were measured before drawing that
conclusion, and both contradicted the obvious assumption:

- "Correcting" the ``-0.186*sin(M)`` term to the textbook ``-0.186*sin(M')``
  makes the fit *worse* (mean error 0.112 -> 0.195 degrees, and it degrades 11040
  of 16072 samples). A truncated series absorbs its own missing terms, so
  changing one argument in isolation is not a fix. Leave it alone.
- Reading the Moon's zodiac sign from ``calc.py`` and from Astronomy Engine
  disagrees on 0.44% of samples, and the phase bucket on 0.21% — these are the
  days where the true value sits within half a degree of a 30-degree or
  45-degree boundary. Not worth changing user-visible output over.

**What the series genuinely cannot do** is give the Moon's distance from Earth,
the true illuminated fraction, when the next quarter falls, or whether an eclipse
is imminent. Those are the facts a reader actually finds interesting, and they
are what this module adds. The phase *name* stays owned by ``calc.py`` so the
altar can never contradict itself: this module reports the phase as a raw angle
and never re-buckets it.

Astronomy Engine is MIT, pure Python and has no dependencies. All searches are
memoised per calendar day — the whole user base shares one day's facts, so the
33 ms cost is paid once a day, not once per user.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from functools import lru_cache

import astronomy as astronomy_engine

# Astronomy Engine's Time takes UT as days since J2000.0, not a Julian day.
_J2000 = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
_SYNODIC_MONTH_DAYS = 29.530588
_AU_KM = 149597870.7
# Reference instant for a calendar day's facts. Matches the 12:00 UTC convention
# already used by ``calc.sign_by_date`` / ``calc.moon_state_by_date``.
_REFERENCE_HOUR_UTC = 12
# How far ahead an eclipse is worth mentioning.
_ECLIPSE_HORIZON_DAYS = 400
# A quarter is "happening" close enough to today that tonight counts.
_IMMINENT_DAYS = 1


class SkyUnavailable(RuntimeError):
    """Raised when the ephemeris cannot answer. Callers must degrade, never crash."""


@dataclass(frozen=True)
class QuarterEvent:
    """A named lunar phase boundary: new, first quarter, full, last quarter."""

    name: str
    when: dt.date
    days_until: int  # negative once the moment has passed

    @property
    def imminent(self) -> bool:
        return abs(self.days_until) <= _IMMINENT_DAYS


@dataclass(frozen=True)
class ApsisEvent:
    """Perigee or apogee — the Moon's closest and farthest approach."""

    name: str
    when: dt.date
    days_until: int
    distance_km: int

    @property
    def imminent(self) -> bool:
        return abs(self.days_until) <= 2


@dataclass(frozen=True)
class EclipseEvent:
    kind: str
    when: dt.date
    days_until: int

    @property
    def imminent(self) -> bool:
        return self.days_until <= 7


@dataclass(frozen=True)
class LunarFacts:
    """Everything this module knows about one calendar day."""

    day: dt.date
    phase_angle: float  # 0 = new, 90 = first quarter, 180 = full, 270 = last
    illumination: float  # 0..1
    age_days: float  # days since the last new moon
    distance_km: int
    quarter: QuarterEvent | None
    apsis: ApsisEvent | None
    eclipse: EclipseEvent | None

    @property
    def illumination_percent(self) -> int:
        return round(self.illumination * 100)


_QUARTERS = (("new", 0.0), ("first_quarter", 90.0), ("full", 180.0), ("last_quarter", 270.0))

_ECLIPSE_NAMES = {
    "Total": "total",
    "Partial": "partial",
    "Penumbral": "penumbral",
    "Annular": "annular",
    "Hybrid": "hybrid",
    "Invalid": "invalid",
}

_APSIS_NAMES = {"Pericenter": "perigee", "Apocenter": "apogee", "Invalid": "invalid"}

_PLANETS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")


def _to_engine_time(moment: dt.datetime):
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.UTC)
    return astronomy_engine.Time((moment - _J2000).total_seconds() / 86400.0)


def _to_datetime(engine_time) -> dt.datetime:
    return _J2000 + dt.timedelta(days=engine_time.ut)


def _reference_moment(day: dt.date) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, _REFERENCE_HOUR_UTC, tzinfo=dt.UTC)


# Astronomy Engine's searches only look forward from a start time. A quarter or
# an apsis that happened earlier on the same day is therefore invisible, which
# is exactly the interesting case: at 184 degrees the Moon passed full around
# nine hours ago, and that is the fact worth telling someone. Every search
# therefore starts a couple of days early, and the nearest-event comparison in
# ``_nearest_quarter`` picks whichever direction lands closest.
_SEARCH_LOOKBEHIND_DAYS = 2


def _nearest_quarter(when, day: dt.date) -> QuarterEvent | None:
    """Return the quarter boundary closest to ``day``, past or future.

    Both directions matter: on the night of a full moon the interesting fact is
    that it is tonight, not that the next one is 29 days out.
    """
    best: QuarterEvent | None = None
    for name, target in _QUARTERS:
        hit = astronomy_engine.SearchMoonPhase(target, when, 35 + _SEARCH_LOOKBEHIND_DAYS)
        if hit is None:
            continue
        event = QuarterEvent(name, _to_datetime(hit).date(), (_to_datetime(hit).date() - day).days)
        if best is None or abs(event.days_until) < abs(best.days_until):
            best = event
    return best


@lru_cache(maxsize=128)
def _facts_for_day(day: dt.date) -> LunarFacts:
    when = _to_engine_time(_reference_moment(day))
    illumination = astronomy_engine.Illumination(astronomy_engine.Body.Moon, when)
    lookbehind = _to_engine_time(_reference_moment(day) - dt.timedelta(days=_SEARCH_LOOKBEHIND_DAYS))

    apsis_event: ApsisEvent | None = None
    apsis = astronomy_engine.SearchLunarApsis(lookbehind)
    if apsis is not None:
        apsis_date = _to_datetime(apsis.time).date()
        apsis_event = ApsisEvent(
            _APSIS_NAMES.get(apsis.kind.name, "apsis"),
            apsis_date,
            (apsis_date - day).days,
            round(apsis.dist_km),
        )

    eclipse_event: EclipseEvent | None = None
    eclipse = astronomy_engine.NextLunarEclipse(when)
    if eclipse is not None:
        peak_date = _to_datetime(eclipse.peak).date()
        days_until = (peak_date - day).days
        if 0 <= days_until <= _ECLIPSE_HORIZON_DAYS:
            eclipse_event = EclipseEvent(
                _ECLIPSE_NAMES.get(eclipse.kind.name, "lunar"), peak_date, days_until
            )

    return LunarFacts(
        day=day,
        phase_angle=astronomy_engine.MoonPhase(when),
        illumination=illumination.phase_fraction,
        age_days=astronomy_engine.MoonPhase(when) / 360.0 * _SYNODIC_MONTH_DAYS,
        distance_km=round(illumination.geo_dist * _AU_KM),
        quarter=_nearest_quarter(lookbehind, day),
        apsis=apsis_event,
        eclipse=eclipse_event,
    )


def lunar_facts(day: dt.date) -> LunarFacts:
    """Return the cached lunar facts for a calendar day.

    Memoised: the first caller of the day pays ~33 ms, everyone after is free.
    """
    try:
        return _facts_for_day(day)
    except Exception as exc:  # noqa: BLE001 - the altar must still render
        raise SkyUnavailable(str(exc)) from exc


@lru_cache(maxsize=128)
def _planet_signs(day: dt.date) -> tuple[tuple[str, int], ...]:
    when = _to_engine_time(_reference_moment(day))
    signs = []
    for planet in _PLANETS:
        lon = astronomy_engine.Ecliptic(
            astronomy_engine.GeoVector(getattr(astronomy_engine.Body, planet), when, False)
        ).elon
        signs.append((planet.lower(), int(lon // 30) % 12))
    return tuple(signs)


def planet_signs(day: dt.date) -> dict[str, int]:
    """Geocentric zodiac sign index for the visible planets, memoised per day."""
    try:
        return dict(_planet_signs(day))
    except Exception as exc:  # noqa: BLE001
        raise SkyUnavailable(str(exc)) from exc


# Quarter names map onto the two-step phase vocabulary already translated in
# ``calc.PHASE_NAMES`` for anyone who needs a bare noun, and onto the dedicated
# per-quarter i18n keys used by ``notable_events``.
_PHASE_INDEX_FOR_QUARTER = {"new": 0, "first_quarter": 2, "full": 4, "last_quarter": 6}
_QUARTER_KEYS = {
    "new": "new",
    "first_quarter": "first_quarter",
    "full": "full",
    "last_quarter": "last_quarter",
}


def quarter_name(lang: str, quarter: str) -> str:
    """Bare quarter noun in the given language (nominative, for reuse elsewhere)."""
    from .calc import PHASE_NAMES

    index = _PHASE_INDEX_FOR_QUARTER.get(quarter, 0)
    return PHASE_NAMES.get(lang, PHASE_NAMES["ru"])[index]


def quarter_key(quarter: str) -> str:
    """Map a quarter name onto the i18n key suffix used for it."""
    return _QUARTER_KEYS.get(quarter, "full")


def notable_events(lang: str, facts: LunarFacts) -> list[str]:
    """Return the lines worth showing under the altar, most notable first.

    Deliberately short. A quarter or a perigee only speaks when it is tonight or
    within a day or two; further out it is trivia that dilutes the reading. The
    eclipse is rarer, so it gets a longer horizon.

    Every quarter has its own string per timeframe rather than a shared
    ``{name}`` slot. Russian inflects for case and gender, so "Полнолуние был
    вчера" is simply wrong and no single frame can be correct for all four
    quarter nouns.
    """
    from ..i18n import t

    lines: list[str] = []
    quarter = facts.quarter
    if quarter is not None and quarter.imminent:
        key = quarter_key(quarter.name)
        if quarter.days_until == 0:
            lines.append(t(lang, f"sky_quarter_today_{key}"))
        elif quarter.days_until > 0:
            lines.append(t(lang, f"sky_quarter_in_{key}_days", n=quarter.days_until))
        else:
            lines.append(t(lang, f"sky_quarter_past_{key}"))
    apsis = facts.apsis
    if apsis is not None and apsis.imminent:
        if apsis.days_until == 0:
            lines.append(t(lang, f"sky_apsis_today_{apsis.name}"))
        else:
            lines.append(t(lang, f"sky_{apsis.name}_in_days", n=abs(apsis.days_until)))
    if facts.eclipse is not None and facts.eclipse.imminent:
        lines.append(
            t(
                lang,
                "sky_eclipse_soon",
                kind=t(lang, f"sky_eclipse_{facts.eclipse.kind}"),
                n=facts.eclipse.days_until,
            )
        )
    return lines


def altar_lines(lang: str, facts: LunarFacts) -> list[str]:
    """The illumination line plus whatever is notable enough to say."""
    from ..i18n import t

    return [
        t(lang, "sky_illumination", n=facts.illumination_percent),
        *notable_events(lang, facts),
    ]


def safe_altar_lines(lang: str, day: dt.date) -> list[str]:
    """``altar_lines`` that cannot raise.

    A missing ephemeris costs the user one line of flavour text, never the
    altar itself, so callers cannot get this wrong by forgetting a guard.
    """
    try:
        return altar_lines(lang, lunar_facts(day))
    except SkyUnavailable:
        return []
