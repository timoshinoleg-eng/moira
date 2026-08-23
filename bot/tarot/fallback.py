"""Deterministic, question-aware fallback composer for tarot readings.

This is the product's reliable local path: it never needs an LLM or a network
connection, but still connects the selected spread, the user's *type* of
question, card orientation, position, and card-level light/shadow/advice.
"""
from __future__ import annotations

from .spreads import DrawnCard, position_meaning


def _question_lens(lang: str, question: str | None) -> str:
    """Classify the question into a deliberately broad, privacy-safe lens.

    The raw question is intentionally not copied into the stored interpretation
    or share output.  The lens keeps a local reading relevant without making a
    claim about private facts or leaking the question through a share card.
    """
    text = (question or "").strip().lower()
    if not text or text == "-":
        return "общей жизненной ситуации" if lang == "ru" else "a general life situation"

    groups = (
        (
            ("люб", "отнош", "партн", "свидан", "близост", "семь", "отношен", "relationship", "partner", "dating", "intimacy"),
            "динамике отношений" if lang == "ru" else "relationship dynamics",
        ),
        (
            ("работ", "карьер", "проект", "учеб", "команд", "business", "work", "career", "project", "study"),
            "работе и самореализации" if lang == "ru" else "work and self-realisation",
        ),
        (
            ("выб", "реш", "между", "стоит", "путь", "option", "choose", "decision", "path", "should i"),
            "выборе и критерии решения" if lang == "ru" else "a choice and its decision criterion",
        ),
        (
            ("перемен", "нов", "нача", "переезд", "измен", "change", "new", "start", "move", "transition"),
            "переменах и следующем этапе" if lang == "ru" else "change and the next stage",
        ),
        (
            ("страх", "границ", "уверен", "себ", "тревог", "fear", "boundary", "confidence", "myself", "anxious"),
            "внутренней опоре и личных границах" if lang == "ru" else "inner support and personal boundaries",
        ),
    )
    for markers, lens in groups:
        if any(marker in text for marker in markers):
            return lens
    return "конкретном личном запросе" if lang == "ru" else "a concrete personal question"


def _orientation(lang: str, reversed_: bool) -> str:
    if lang == "ru":
        return "перевёрнутая" if reversed_ else "прямая"
    return "reversed" if reversed_ else "upright"


def _detect_pattern(drawn: list[DrawnCard]) -> str:
    """Backward-compatible compact Russian pattern signal for integrations."""
    return _balance_sentence("ru", drawn) + (" " + _reversal_sentence("ru", drawn) if any(d.reversed for d in drawn) else "")


def _detect_pattern_en(drawn: list[DrawnCard]) -> str:
    """Backward-compatible compact English pattern signal for integrations."""
    return _balance_sentence("en", drawn) + (" " + _reversal_sentence("en", drawn) if any(d.reversed for d in drawn) else "")


def _balance_sentence(lang: str, drawn: list[DrawnCard]) -> str:
    majors = sum(d.card.arcana == "major" for d in drawn)
    minors = len(drawn) - majors
    if lang == "ru":
        if majors == len(drawn) and len(drawn) > 1:
            return "Все карты — Старшие Арканы: здесь заметен важный жизненный урок, а не только бытовая деталь."
        if majors:
            return f"Старший Арканов: {majors}, младших: {minors}; внутренний смысл и практические обстоятельства здесь связаны."
        return "Младшие Арканы держат фокус на наблюдаемых действиях, привычках и отношениях в повседневности."
    if majors == len(drawn) and len(drawn) > 1:
        return "All cards are Major Arcana: this points to an important life lesson, not only a practical detail."
    if majors:
        return f"There are {majors} Major and {minors} Minor Arcana, linking an inner theme with practical circumstances."
    return "The Minor Arcana keep the focus on observable actions, habits, and everyday relationship dynamics."


def _reversal_sentence(lang: str, drawn: list[DrawnCard]) -> str:
    count = sum(d.reversed for d in drawn)
    if not count:
        return "" if lang == "ru" else ""
    if lang == "ru":
        return (
            "Перевёрнутая карта просит не ускорять выводы и проверить, где энергия уже есть, "
            "но пока выражается не прямо."
            if count == 1
            else "Несколько перевёрнутых карт указывают на внутреннюю работу, задержку или необходимость пересобрать привычный способ действия."
        )
    return (
        "The reversed card asks for a slower conclusion: energy may be present but not yet expressed directly."
        if count == 1
        else "Several reversed cards point to inner work, a delay, or a need to rethink the usual way of acting."
    )


def _connection_sentence(lang: str, spread_id: str, drawn: list[DrawnCard]) -> str:
    """Connect the positions instead of appending three isolated mini-definitions."""
    if len(drawn) < 2:
        return ""
    names = [d.card.name(lang) for d in drawn]
    labels = [d.position_label.get(lang, d.position_label["ru"]) for d in drawn]
    if lang == "ru":
        if spread_id == "situation" and len(drawn) >= 3:
            return (
                f"«{names[0]}» в позиции «{labels[0]}» задаёт исходную динамику; "
                f"«{names[1]}» показывает, что её усложняет или дополняет, а «{names[2]}» переводит это в направление действия."
            )
        if spread_id == "love" and len(drawn) >= 3:
            return (
                f"«{names[0]}» описывает вашу точку опоры, «{names[1]}» — динамику связи, "
                f"а «{names[2]}» подсказывает, что можно бережно поддержать без предположений о чужих мыслях."
            )
        if spread_id == "choice" and len(drawn) >= 3:
            return (
                f"«{names[0]}» раскрывает цену и потенциал пути А, «{names[1]}» — пути Б, "
                f"а «{names[2]}» помогает сформулировать критерий, по которому решение останется вашим."
            )
        return f"Позиции «{labels[0]}» и «{labels[1]}» стоит читать вместе: «{names[0]}» меняет акцент «{names[1]}»."
    if spread_id == "situation" and len(drawn) >= 3:
        return (
            f"{names[0]} in “{labels[0]}” sets the starting dynamic; {names[1]} shows what complicates or completes it, "
            f"and {names[2]} turns that link into a direction for action."
        )
    if spread_id == "love" and len(drawn) >= 3:
        return (
            f"{names[0]} describes your point of support, {names[1]} the relationship dynamic, "
            f"and {names[2]} what can be nurtured without claiming to know another person's mind."
        )
    if spread_id == "choice" and len(drawn) >= 3:
        return (
            f"{names[0]} shows the potential and cost of path A, {names[1]} of path B, "
            f"and {names[2]} helps frame a criterion so the choice remains yours."
        )
    return f"Read “{labels[0]}” and “{labels[1]}” together: {names[0]} changes the emphasis of {names[1]}."


def _field(drawn: DrawnCard, name: str, lang: str) -> str:
    meanings = drawn.card.localized(lang).reversed if drawn.reversed else drawn.card.localized(lang).upright
    return getattr(meanings, name) or meanings.essence


def compose_fallback_reading(
    lang: str,
    spread_id: str,
    drawn: list[DrawnCard],
    question: str | None = None,
) -> dict:
    """Build a complete local reading with no LLM or network dependency.

    The raw question is converted to a privacy-safe thematic lens.  Every card
    still contributes its exact orientation, spread position, essence,
    light/shadow/advice fields, and its relationship with the other positions.
    """
    lang = "ru" if lang == "ru" else "en"
    is_ru = lang == "ru"
    lens = _question_lens(lang, question)
    card_texts: list[str] = []
    plain_parts: list[str] = []

    for drawn_card in drawn:
        label = drawn_card.position_label.get(lang, drawn_card.position_label["ru"])
        position = position_meaning(spread_id, drawn_card.position_id, lang)
        meanings = drawn_card.card.localized(lang).reversed if drawn_card.reversed else drawn_card.card.localized(lang).upright
        orientation = _orientation(lang, drawn_card.reversed)
        if is_ru:
            details = [
                f"<i>{label}</i> ({position}; {orientation}): {meanings.essence}",
                f"Ресурс позиции: {meanings.light}" if meanings.light else "",
                f"Тень для проверки: {meanings.shadow}" if meanings.shadow else "",
                f"Практический шаг: {meanings.advice}" if meanings.advice else "",
            ]
        else:
            details = [
                f"<i>{label}</i> ({position}; {orientation}): {meanings.essence}",
                f"Resource in this position: {meanings.light}" if meanings.light else "",
                f"Shadow to examine: {meanings.shadow}" if meanings.shadow else "",
                f"Practical step: {meanings.advice}" if meanings.advice else "",
            ]
        text = " ".join(part for part in details if part)
        card_texts.append(text)
        plain_parts.append(text.replace("<i>", "").replace("</i>", ""))

    connection = _connection_sentence(lang, spread_id, drawn)
    balance = _balance_sentence(lang, drawn)
    reversals = _reversal_sentence(lang, drawn)
    support = _field(drawn[0], "light", lang) if drawn else ""
    caution = _field(drawn[1] if len(drawn) > 1 else drawn[0], "shadow", lang) if drawn else ""
    next_action = _field(drawn[-1], "advice", lang) if drawn else ""

    if is_ru:
        synthesis = (
            f"Вопрос рассматривается через тему {lens}. {connection} {balance} {reversals} "
            f"Ресурс, который можно использовать: {support}. Важно не обойти вниманием: {caution}. "
            "Вместе карты описывают возможное направление и выбор точки приложения усилий, а не фиксированный исход."
        ).strip()
        practical_focus = (
            f"Для запроса о {lens} выберите один наблюдаемый шаг на ближайшее время: {next_action} "
            "После него проверьте по фактам, стало ли больше ясности и опоры, вместо того чтобы требовать от карт окончательного ответа."
        )
        reflection = (
            drawn[-1].card.localized(lang).reflection_question
            if drawn and drawn[-1].card.localized(lang).reflection_question
            else f"Какой небольшой шаг в теме {lens} подтвердит ваше решение делом, а не только надеждой?"
        )
        headline = "Трактовка расклада"
        opening = (
            f"Карты рассматривают тему {lens} через роли позиций и взаимосвязь символов. "
            "Это повод заметить тенденции и выбрать осознанный шаг, а не обещание заранее заданного будущего."
        )
        share_summary = (
            f"В раскладе {', '.join(d.card.name(lang) for d in drawn)} акцентируют путь от наблюдения к действию. "
            f"Полезный фокус: {next_action}"
        )
        voice_text = f"Расклад. {' '.join(plain_parts)}. {synthesis} {practical_focus} Вопрос для размышления: {reflection}"
    else:
        synthesis = (
            f"The question is read through {lens}. {connection} {balance} {reversals} "
            f"A resource to use is: {support}. What deserves a closer look is: {caution}. "
            "Together the cards suggest a possible direction and a place to put effort, not a fixed outcome."
        ).strip()
        practical_focus = (
            f"For {lens}, choose one observable next step: {next_action} "
            "Then check the evidence for more clarity and support instead of asking the cards for a final verdict."
        )
        reflection = (
            drawn[-1].card.localized(lang).reflection_question
            if drawn and drawn[-1].card.localized(lang).reflection_question
            else f"What small action in {lens} would let you test this reading in real life?"
        )
        headline = "Reading interpretation"
        opening = (
            f"The cards explore {lens} through the roles of the positions and the relationship between symbols. "
            "They invite you to notice tendencies and choose a conscious step, not accept a pre-written future."
        )
        share_summary = (
            f"In this reading, {', '.join(d.card.name(lang) for d in drawn)} highlight a path from noticing to action. "
            f"A useful focus: {next_action}"
        )
        voice_text = f"Reading. {' '.join(plain_parts)}. {synthesis} {practical_focus} Reflection question: {reflection}"

    plain_text = ". ".join(plain_parts + [synthesis, practical_focus, reflection])
    return {
        "headline": headline,
        "opening": opening,
        "card_texts": card_texts,
        "synthesis": synthesis,
        "practical_focus": practical_focus,
        "reflection_question": reflection,
        "voice_text": voice_text,
        "plain_text": plain_text,
        "share_summary": share_summary,
        "question_lens": lens,
    }


def compose_followup(
    lang: str,
    spread_id: str,
    drawn: list[DrawnCard],
    question: str | None,
    kind: str,
) -> str:
    """Continue a saved reading without drawing new random cards.

    Follow-ups deliberately reuse the original cards and question lens. This
    keeps a continuation grounded in the saved reading rather than creating a
    second, unexplained lottery draw.
    """
    lang = "ru" if lang == "ru" else "en"
    if not drawn:
        return "Расклад больше недоступен." if lang == "ru" else "This saved reading is no longer available."
    lens = _question_lens(lang, question)
    focus = drawn[-1] if kind == "next" else drawn[0]
    if kind == "hidden" and len(drawn) > 1:
        focus = drawn[1]
    label = focus.position_label.get(lang, focus.position_label["ru"])
    orientation = _orientation(lang, focus.reversed)
    meaning = _field(focus, "essence", lang)
    light = _field(focus, "light", lang)
    shadow = _field(focus, "shadow", lang)
    advice = _field(focus, "advice", lang)

    if lang == "ru":
        if kind == "hidden" and len(drawn) > 1:
            first = drawn[0]
            return (
                f"<b>Скрытый слой расклада</b>\n\nВ теме {lens} вернитесь к позиции «{label}»: "
                f"«{focus.card.name(lang)}» ({orientation}) показывает {meaning} "
                f"рядом с «{first.card.name(lang)}» в позиции «{first.position_label.get(lang, first.position_label['ru'])}». "
                f"Ресурс здесь — {light}. Проверьте, не проявляется ли тень: {shadow}. "
                f"Полезный способ исследовать это без новых карт: {advice}"
            )
        if kind == "next":
            return (
                f"<b>Следующий шаг</b>\n\nДля темы {lens} позиция «{label}» несёт «{focus.card.name(lang)}» ({orientation}): {meaning} "
                f"Начните не с большого предсказания, а с проверяемого действия: {advice} "
                f"Его ресурс — {light}; помните о риске: {shadow}."
            )
        return (
            f"<b>Карта глубже</b>\n\n«{focus.card.name(lang)}» в позиции «{label}» ({orientation}) "
            f"возвращает расклад к теме {lens}: {meaning} Ресурс карты — {light}. "
            f"Тень, которую полезно заметить: {shadow}. Практика на ближайшее время: {advice}"
        )
    if kind == "hidden" and len(drawn) > 1:
        first = drawn[0]
        return (
            f"<b>The hidden layer</b>\n\nFor {lens}, return to “{label}”: “{focus.card.name(lang)}” ({orientation}) "
            f"shows {meaning} beside “{first.card.name(lang)}” in “{first.position_label.get(lang, first.position_label['ru'])}”. "
            f"The resource here is {light}. Check whether this shadow is present: {shadow}. "
            f"A way to explore it without new cards: {advice}"
        )
    if kind == "next":
        return (
            f"<b>The next step</b>\n\nFor {lens}, “{focus.card.name(lang)}” in “{label}” ({orientation}) suggests: {meaning} "
            f"Start with an observable action rather than a large prediction: {advice} "
            f"Its resource is {light}; keep this risk in view: {shadow}."
        )
    return (
        f"<b>One card, more deeply</b>\n\n“{focus.card.name(lang)}” in “{label}” ({orientation}) "
        f"brings the reading back to {lens}: {meaning} Its resource is {light}. "
        f"A shadow worth noticing: {shadow}. A practice for now: {advice}"
    )
