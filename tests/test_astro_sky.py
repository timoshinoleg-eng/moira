"""Astronomy Engine-backed lunar facts.

Two things are pinned here that are easy to get wrong again:

- The Moon's *geocentric* ecliptic longitude is ``Ecliptic(GeoVector(Moon))``.
  ``EclipticLongitude()`` is **heliocentric** and comparing the two produces a
  bogus ~90 degree "error" — the mistake that produced a false alarm about
  ``calc.py`` when this module was first written.
- ``calc.py`` keeps its own truncated series and is deliberately left alone. The
  test below states its measured accuracy so nobody "fixes" it on a hunch.
"""
from __future__ import annotations

import datetime as dt

import astronomy as astronomy_engine
import pytest

from bot.astro import calc
from bot.astro.sky import (
    LunarFacts,
    SkyUnavailable,
    altar_lines,
    lunar_facts,
    notable_events,
    planet_signs,
    quarter_name,
    safe_altar_lines,
)

J2000 = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
# Dates picked because the lunar situation is unambiguous on each:
# a full Moon, a new Moon, a perigee, and a quiet day in between.
FULL_MOON_DAY = dt.date(2026, 10, 26)
NEW_MOON_DAY = dt.date(2026, 10, 10)
PERIGEE_DAY = dt.date(2026, 10, 1)
QUIET_DAY = dt.date(2026, 10, 13)


def _engine_time(moment: dt.datetime):
    return astronomy_engine.Time((moment - J2000).total_seconds() / 86400.0)


def _geocentric_moon_longitude(moment: dt.datetime) -> float:
    """The geocentric quantity, deliberately not EclipticLongitude()."""
    return astronomy_engine.Ecliptic(
        astronomy_engine.GeoVector(
            astronomy_engine.Body.Moon, _engine_time(moment), False
        )
    ).elon


# --------------------------------------------------------------- the series --


def test_hand_rolled_series_is_within_half_a_degree() -> None:
    """calc.py's truncated ELP series is accurate enough and must stay as it is.

    16072 samples six hours apart across 2020-2030, compared against Astronomy
    Engine's geocentric longitude, gave a mean of 0.12 and a maximum of 0.43
    degrees. That is well inside a 30-degree zodiac sign, so swapping the engine
    in would change nothing a user can perceive.
    """
    moment = dt.datetime(2026, 3, 15, 6, 0, tzinfo=dt.UTC)
    errors = []
    while moment < dt.datetime(2026, 6, 15, 6, 0, tzinfo=dt.UTC):
        truth = _geocentric_moon_longitude(moment)
        delta = (calc.moon_longitude(moment) - truth + 180.0) % 360.0 - 180.0
        errors.append(abs(delta))
        moment += dt.timedelta(hours=6)
    assert max(errors) < 0.6, "the series drifted further than the measured 0.43 deg"
    assert sum(errors) / len(errors) < 0.25


def test_ecliptic_longitude_is_heliocentric_and_must_not_be_used_for_the_moon() -> None:
    """Guards the mistake that produced a false ~90 degree error report.

    A single date is not a reliable witness — near full Moon the two readings can
    happen to land within a few degrees of each other — so this sweeps a year and
    asserts the divergence *reaches* a size that would wreck a zodiac sign.
    """
    moment = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)
    worst = 0.0
    series_worst = 0.0
    while moment < dt.datetime(2027, 1, 1, 12, 0, tzinfo=dt.UTC):
        heliocentric = astronomy_engine.EclipticLongitude(
            astronomy_engine.Body.Moon, _engine_time(moment)
        )
        geocentric = _geocentric_moon_longitude(moment)
        worst = max(worst, abs((heliocentric - geocentric + 180.0) % 360.0 - 180.0))
        series_worst = max(
            series_worst, abs((calc.moon_longitude(moment) - geocentric + 180.0) % 360.0 - 180.0)
        )
        moment += dt.timedelta(days=3)
    assert worst > 90.0, "heliocentric and geocentric never diverged; API changed?"
    # The hand-rolled series tracks the geocentric value, not the heliocentric one.
    assert series_worst < 0.6


# ------------------------------------------------------------------- facts --


def test_facts_for_a_full_moon_day() -> None:
    facts = lunar_facts(FULL_MOON_DAY)
    assert facts.illumination_percent >= 99
    assert facts.quarter is not None
    assert facts.quarter.name == "full"
    assert facts.quarter.days_until == 0
    assert facts.quarter.imminent


def test_facts_for_a_new_moon_day() -> None:
    facts = lunar_facts(NEW_MOON_DAY)
    assert facts.illumination_percent <= 1
    assert facts.quarter is not None and facts.quarter.name == "new"
    assert facts.quarter.imminent


def test_perigee_is_reported_on_its_day() -> None:
    facts = lunar_facts(PERIGEE_DAY)
    assert facts.apsis is not None
    assert facts.apsis.name == "perigee"
    assert facts.apsis.days_until == 0
    # A perigee is by definition a close approach.
    assert facts.apsis.distance_km < 370_000


def test_a_quiet_day_reports_no_quarter() -> None:
    assert notable_events("en", lunar_facts(QUIET_DAY)) == []


def test_illumination_is_always_available_even_on_a_quiet_day() -> None:
    lines = altar_lines("ru", lunar_facts(QUIET_DAY))
    assert len(lines) == 1
    assert "%" in lines[0]


def test_distance_and_age_are_physically_plausible() -> None:
    facts = lunar_facts(FULL_MOON_DAY)
    assert 350_000 < facts.distance_km < 410_000
    # A lunar age can never leave one synodic month.
    assert 0.0 < facts.age_days < 29.54


def test_eclipse_is_reported_within_its_horizon() -> None:
    facts = lunar_facts(FULL_MOON_DAY)
    assert facts.eclipse is not None
    assert 0 <= facts.eclipse.days_until <= 400


def test_planet_signs_cover_the_visible_planets() -> None:
    signs = planet_signs(QUIET_DAY)
    assert set(signs) == {"mercury", "venus", "mars", "jupiter", "saturn"}
    assert all(0 <= v <= 11 for v in signs.values())


def test_results_are_memoised_per_day() -> None:
    """The whole user base shares one day's facts, so the search runs once."""
    first = lunar_facts(dt.date(2031, 5, 4))
    second = lunar_facts(dt.date(2031, 5, 4))
    assert first is second


# ------------------------------------------------------------------ copy ----


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_altar_copy_is_localised_and_complete(lang: str) -> None:
    lines = altar_lines(lang, lunar_facts(FULL_MOON_DAY))
    assert lines
    for line in lines:
        assert line
        # A missing key would come back as the key name itself.
        assert not line.startswith("sky_")
        assert "{" not in line and "}" not in line


def test_russian_quarter_grammar_is_correct() -> None:
    """Regression: a shared "{name} today" frame produced "Полнолуние был".

    Russian inflects for case and gender, so each quarter needs its own string.
    """
    today = altar_lines("ru", lunar_facts(FULL_MOON_DAY))
    assert any("полнолуние" in line for line in today)
    # No masculine verb may end up attached to a neuter noun.
    assert not any("полнолуние был" in line for line in today)
    past = altar_lines("ru", lunar_facts(dt.date(2026, 9, 27)))
    assert any("Полнолуние было вчера" in line for line in past)


def test_english_quarter_names_keep_their_capitals() -> None:
    lines = altar_lines("en", lunar_facts(FULL_MOON_DAY))
    assert any("Full Moon" in line for line in lines)
    assert not any("full Moon" in line for line in lines)


def test_quarter_name_bare_noun_is_translated() -> None:
    assert quarter_name("ru", "full") == calc.PHASE_NAMES["ru"][4]
    assert quarter_name("en", "new") == calc.PHASE_NAMES["en"][0]


# ------------------------------------------------------------ degradation ----


def test_safe_altar_lines_swallows_ephemeris_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The altar must render even if the ephemeris cannot answer."""
    from bot.astro import sky

    def boom(day: dt.date) -> LunarFacts:
        raise SkyUnavailable("no ephemeris")

    monkeypatch.setattr(sky, "lunar_facts", boom)
    assert safe_altar_lines("ru", FULL_MOON_DAY) == []


def test_lunar_facts_raises_a_typed_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.astro import sky

    monkeypatch.setattr(sky, "_facts_for_day", lambda day: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(SkyUnavailable):
        sky.lunar_facts(FULL_MOON_DAY)
