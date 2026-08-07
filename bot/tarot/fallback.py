"""Deterministic fallback composer for tarot readings (no LLM required)."""
from __future__ import annotations

from ..i18n import t
from .deck import TarotCard
from .spreads import DrawnCard, POSITION_MEANINGS, position_meaning


def _detect_pattern(drawn: list[DrawnCard]) -> str:
    """Detect one notable pattern in the drawn cards (RU version)."""
    majors = [d for d in drawn if d.card.arcana == "major"]
    reversed_count = sum(1 for d in drawn if d.reversed)

    # All majors
    if len(majors) == len(drawn) and len(drawn) > 1:
        return "Все карты Старшего Аркана: ситуация выходит на уровень важных жизненных уроков."
    # Mostly reversed
    if reversed_count >= 2 and len(drawn) >= 2:
        return "Большинство карт в перевёрнутом положении: энергия направлена внутрь или задерживается."
    # Single major among minors
    if len(majors) == 1 and len(drawn) > 1:
        m = majors[0]
        return f"Карта «{m.card.name_ru}» как главный урок среди младших арканов."
    return ""


def _detect_pattern_en(drawn: list[DrawnCard]) -> str:
    """Detect one notable pattern in the drawn cards (EN version)."""
    majors = [d for d in drawn if d.card.arcana == "major"]
    reversed_count = sum(1 for d in drawn if d.reversed)

    if len(majors) == len(drawn) and len(drawn) > 1:
        return "All Major Arcana: the situation touches on important life lessons."
    if reversed_count >= 2 and len(drawn) >= 2:
        return "Most cards are reversed: energy is turning inward or delayed."
    if len(majors) == 1 and len(drawn) > 1:
        m = majors[0]
        return f"Card «{m.card.name_en}» stands out as the main lesson among the minors."
    return ""


def compose_fallback_reading(
    lang: str,
    spread_id: str,
    drawn: list[DrawnCard],
) -> dict:
    """Build a complete fallback reading without LLM.

    Returns a dict with: headline, opening, card_texts, synthesis, practical_focus,
    reflection_question, voice_text, plain_text.
    """
    is_ru = lang == "ru"
    card_texts = []
    plain_parts = []

    for d in drawn:
        label = d.position_label.get(lang, d.position_label["ru"])
        meaning = d.card.meaning(lang, d.reversed)
        pos_meaning = position_meaning(spread_id, d.position_id, lang)

        if is_ru:
            text = f"<i>{label}</i> ({pos_meaning}): {meaning}"
        else:
            text = f"<i>{label}</i> ({pos_meaning}): {meaning}"
        card_texts.append(text)
        plain_parts.append(f"{label}: {meaning}")

    # Detect pattern
    pattern = _detect_pattern(drawn) if is_ru else _detect_pattern_en(drawn)

    # Build synthesis based on spread type
    if spread_id == "situation":
        if is_ru:
            synthesis = (
                "Ситуация раскрывается через три грани: то, что происходит сейчас, "
                "что остаётся скрытым, и куда стоит направить внимание. "
                "Карты показывают динамику, а не неизбежный итог."
            )
            practical_focus = "Прислушайтесь к скрытому фактору — он может стать ключом к следующему шагу."
            reflection = "Что из того, что вы пока не замечаете, влияет на ситуацию сильнее всего?"
        else:
            synthesis = (
                "The situation unfolds through three lenses: what is happening now, "
                "what remains hidden, and where attention could go next. "
                "The cards show dynamics, not an inevitable outcome."
            )
            practical_focus = "Pay attention to the hidden factor — it may hold the key to the next step."
            reflection = "What are you not yet noticing that affects the situation the most?"
    elif spread_id == "love":
        if is_ru:
            synthesis = (
                "Расклад исследует ваше состояние, динамику связи и то, что стоит поддерживать. "
                "Карты говорят о вероятных тенденциях, а не о чужих мыслях как факте."
            )
            practical_focus = "Сосредоточьтесь на том, что вы можете поддерживать или ослабить в себе и в связи."
            reflection = "Какая потребность в вас сейчас требует большего внимания?"
        else:
            synthesis = (
                "The spread explores your state, the relationship dynamic, and what to nurture. "
                "The cards speak of likely tendencies, not another person's thoughts as fact."
            )
            practical_focus = "Focus on what you can nurture or ease up on in yourself and the connection."
            reflection = "Which need in you right now asks for more attention?"
    elif spread_id == "choice":
        if is_ru:
            synthesis = (
                "Два пути имеют разный потенциал, ограничения и цену. "
                "Карты не выбирают за вас — они показывают, что важно учесть при решении."
            )
            practical_focus = "Сравните не только выгоды, но и то, чем каждый путь просит пожертвовать."
            reflection = "Какой критерий для вас важнее всего — и какой вы пока недооцениваете?"
        else:
            synthesis = (
                "The two paths carry different potential, limitations, and costs. "
                "The cards do not choose for you — they show what matters when deciding."
            )
            practical_focus = "Compare not only the benefits, but what each path asks you to give up."
            reflection = "Which criterion matters most to you — and which are you underestimating?"
    else:
        if is_ru:
            synthesis = "Карты раскрывают тему расклада через несколько граней."
            practical_focus = "Обратите внимание на то, что повторяется в картах."
            reflection = "Что в этих картах откликается вам сильнее всего?"
        else:
            synthesis = "The cards reveal the spread's theme through several lenses."
            practical_focus = "Notice what repeats across the cards."
            reflection = "What in these cards resonates with you the most?"

    if pattern:
        synthesis += (" " + pattern) if is_ru else (" " + pattern)

    # Build voice text
    if is_ru:
        voice_text = f"Расклад. {' '.join(plain_parts)}. {synthesis}"
    else:
        voice_text = f"Reading. {' '.join(plain_parts)}. {synthesis}"

    # Build headline
    if is_ru:
        headline = "Трактовка расклада"
    else:
        headline = "Reading interpretation"

    # Build opening
    if is_ru:
        opening = "Без подключения ИИ карты говорят на языке символов и ассоциаций."
    else:
        opening = "Without AI, the cards speak through symbols and associations."

    plain_text = ". ".join(plain_parts)
    if pattern:
        plain_text += ". " + pattern
    plain_text += ". " + synthesis

    return {
        "headline": headline,
        "opening": opening,
        "card_texts": card_texts,
        "synthesis": synthesis,
        "practical_focus": practical_focus,
        "reflection_question": reflection,
        "voice_text": voice_text,
        "plain_text": plain_text,
    }
