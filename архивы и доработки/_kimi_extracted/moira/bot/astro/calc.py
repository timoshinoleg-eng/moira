from __future__ import annotations

import math
import random
from datetime import date, datetime, timezone

ZODIAC_NAMES = {
    "ru": [
        "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
        "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы",
    ],
    "en": [
        "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
    ],
}

ZODIAC_ELEMENT = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]  # fire earth air water
ELEMENT_NAMES = {
    "ru": ["Огня", "Земли", "Воздуха", "Воды"],
    "en": ["Fire", "Earth", "Air", "Water"],
}

PHASE_NAMES = {
    "ru": [
        "Новолуние", "Растущий серп", "Первая четверть", "Растущая Луна",
        "Полнолуние", "Убывающая Луна", "Последняя четверть", "Убывающий серп",
    ],
    "en": [
        "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
        "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
    ],
}

PHASE_TEXTS = {
    "ru": [
        "время замыслов и тихих стартов",
        "первые шаги набирают силу",
        "день решений и действий",
        "энергия растёт — вкладывай её в важное",
        "пик силы: желания слышны ясно",
        "время благодарности и завершений",
        "отпусти лишнее",
        "тишина перед обновлением",
    ],
    "en": [
        "a time for intentions and quiet starts",
        "first steps gain strength",
        "a day of decisions and action",
        "energy is rising — invest it in what matters",
        "peak power: wishes are heard clearly",
        "a time for gratitude and completion",
        "let go of the excess",
        "stillness before renewal",
    ],
}

MOON_SIGN_TEXTS = {
    "ru": [
        "луна подталкивает действовать смело и начинать",
        "время укреплять то, что уже создано",
        "день лёгких разговоров и новостей",
        "эмоции глубже обычного — береги близких",
        "центр внимания и творчества",
        "время порядка, деталей и заботы",
        "ищи гармонию и договорённости",
        "день сильных чувств и трансформации",
        "время расширять горизонты",
        "упорство приносит плоды",
        "день идей и дружбы",
        "доверься интуиции и снам",
    ],
    "en": [
        "the moon pushes to act boldly and begin",
        "time to strengthen what is already built",
        "a day of light talks and news",
        "emotions run deeper — take care of loved ones",
        "the spotlight of attention and creativity",
        "time for order, details and care",
        "seek harmony and agreements",
        "a day of strong feelings and transformation",
        "time to widen your horizons",
        "persistence bears fruit",
        "a day of ideas and friendship",
        "trust your intuition and dreams",
    ],
}

PERSONAL_SAME_ELEMENT = {
    "ru": "Луна сегодня в твоей стихии ({el}) — день тебе созвучен.",
    "en": "The Moon is in your element today ({el}) — the day resonates with you.",
}

PERSONAL_OTHER_ELEMENT = {
    "ru": "Луна сегодня в стихии {moon_el}, твоя стихия — {self_el}: день просит мягкости.",
    "en": "The Moon is in the {moon_el} element today, yours is {self_el}: the day asks for gentleness.",
}


def _normalize(deg: float) -> float:
    return deg % 360.0


def julian_day(dt: datetime) -> float:
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def moon_longitude(dt: datetime) -> float:
    jd = julian_day(dt)
    T = (jd - 2451545.0) / 36525.0
    Lp = _normalize(218.3164477 + 481267.88123421 * T - 0.0015786 * T * T)
    D = _normalize(297.8501921 + 445267.1114034 * T - 0.0018819 * T * T)
    M = _normalize(357.5291092 + 35999.0502909 * T - 0.0001536 * T * T)
    Mp = _normalize(134.9633964 + 477198.8675055 * T + 0.0087414 * T * T)
    F = _normalize(93.2720950 + 483202.0175233 * T - 0.0036539 * T * T)
    r = math.radians
    lon = (
        Lp
        + 6.289 * math.sin(r(Mp))
        + 1.274 * math.sin(r(2 * D - Mp))
        + 0.658 * math.sin(r(2 * D))
        + 0.214 * math.sin(r(2 * Mp))
        - 0.186 * math.sin(r(M))
        - 0.114 * math.sin(r(2 * F))
        + 0.059 * math.sin(r(2 * Mp - 2 * D))
        + 0.057 * math.sin(r(Mp - 2 * D + M))
        + 0.053 * math.sin(r(Mp + 2 * D))
        - 0.046 * math.sin(r(2 * D - M))
        - 0.041 * math.sin(r(Mp - M))
    )
    return _normalize(lon)


def sun_longitude(dt: datetime) -> float:
    jd = julian_day(dt)
    T = (jd - 2451545.0) / 36525.0
    L0 = _normalize(280.46646 + 36000.76983 * T + 0.0003032 * T * T)
    M = _normalize(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    r = math.radians
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(r(M))
        + (0.019993 - 0.000101 * T) * math.sin(r(2 * M))
        + 0.000289 * math.sin(r(3 * M))
    )
    true_lon = L0 + C
    omega = 125.04 - 1934.136 * T
    return _normalize(true_lon - 0.00569 - 0.00478 * math.sin(r(omega)))


def sun_sign_index(dt: datetime) -> int:
    return int(sun_longitude(dt) // 30) % 12


def moon_state(dt: datetime) -> tuple[int, float, int]:
    """Return (phase_index 0..7, illumination 0..1, moon_sign_index 0..11)."""
    m = moon_longitude(dt)
    s = sun_longitude(dt)
    angle = _normalize(m - s)
    illum = (1 - math.cos(math.radians(angle))) / 2
    phase = int(((angle / 45.0) + 0.5)) % 8
    sign = int(m // 30) % 12
    return phase, illum, sign


def daily_card(day: date, user_id: int):
    """Deterministic card of the day: (TarotCard, reversed)."""
    from ..tarot.deck import build_deck

    rng = random.Random(day.isoformat() + "#" + str(user_id))
    deck = build_deck()
    card = deck[rng.randrange(len(deck))]
    reversed_ = rng.random() < 0.33
    return card, reversed_


def sign_by_date(day: date) -> int:
    dt = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
    return sun_sign_index(dt)


def moon_state_by_date(day: date) -> tuple[int, float, int]:
    dt = datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
    return moon_state(dt)
