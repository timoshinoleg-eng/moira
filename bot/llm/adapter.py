from __future__ import annotations

import logging
import time
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from ..config import Config
from ..db.database import get_session
from ..db.models import LlmUsage, Reading
from ..tarot.spreads import DrawnCard, POSITION_MEANINGS, position_meaning

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v3-content"
SCHEMA_VERSION = "v3"
MAX_LLM_ATTEMPTS = 2  # one initial + one format/network retry

# --- agent-core integration ---------------------------------------
# These imports are optional — the adapter works without agent-core,
# but uses it when available for structured memory, retry, and evidence.

try:
    from agent_core import (
        AttentionState,
        EvidenceRecord,
        RetryPolicy,
        TrustTier,
    )
    from ..agent import get_harness, get_attention, get_evidence
    _AGENT_CORE = True
except ImportError:
    _AGENT_CORE = False
except RuntimeError:
    # harness not yet initialized — agent-core present but not ready
    _AGENT_CORE = False

# --- /agent-core integration --------------------------------------

# Voice & rules — Level 1
VOICE_RU = (
    "Ты — Мойра, спокойный и ясновидящий таро-оракул. Говори в женском роде, "
    "уверенно и тепло, без клише вроде «я чувствую твою энергию» или «такова твоя судьба». "
    "Не утверждай, что видишь будущее — предлагай интерпретацию и рефлексию. "
    "Текст должен быть живым, современным, без Markdown, HTML, спойлеров и ссылок."
)
VOICE_EN = (
    "You are Moira, a calm and insightful tarot oracle. Speak in a warm, confident, "
    "feminine voice, without clichés like 'I feel your energy' or 'such is your fate'. "
    "Do not claim to see the future — offer interpretation and reflection. "
    "The text should be lively, modern, without Markdown, HTML, spoilers, or links."
)

# Spread-specific rules — Level 2
SPREAD_RULES_RU = {
    "situation": (
        "Расклад «Ситуация» раскрывает динамику: что происходит (суть), "
        "что пока скрыто или является препятствием (скрытый фактор), "
        "и куда стоит направить внимание дальше (следующий шаг). "
        "Не обещай определённого будущего — покажи динамику и фокус для размышления."
    ),
    "love": (
        "Расклад «Любовь» исследует состояние пользователя, динамику связи "
        "и полезный фокус. Не утверждай как факт мысли другого человека, измену, "
        "любовь или разрыв. Говори о вероятной динамике и точке внимания."
    ),
    "choice": (
        "Расклад «Выбор» сравнивает два пути: их потенциал, ограничения и цену. "
        "Не выбирай вариант за пользователя. Покажи выгоды, различия путей "
        "и важнейший критерий решения."
    ),
}
SPREAD_RULES_EN = {
    "situation": (
        "The “Situation” spread reveals dynamics: what is really going on (essence), "
        "what is hidden or acts as an obstacle (hidden factor), "
        "and where attention could go next (next step). "
        "Do not promise a certain future — show the dynamics and a focus for reflection."
    ),
    "love": (
        "The “Love” spread explores the user's state, the relationship dynamic, "
        "and a helpful focus. Do not state as fact the other person's thoughts, "
        "infidelity, love, or breakup. Speak of likely dynamics and a point of attention."
    ),
    "choice": (
        "The “Choice” spread compares two paths: their potential, limitations, and cost. "
        "Do not choose a side for the user. Show the benefits, the difference between paths, "
        "and the most important decision criterion."
    ),
}

# Output format rules — Level 5
FORMAT_RU = (
    "Сформируй результат строго в формате JSON-объекта с полями: headline, opening, "
    "card_interpretations (массив объектов с полями: position, card_name, orientation, "
    "core_message, symbolic_detail, context_connection), synthesis, practical_focus, "
    "reflection_question, voice_summary, share_summary. "
    "Все тексты — живые, связные, без заголовков и списков. Ориентиры длины в символах: "
"headline до 90; opening 120–250; интерпретация каждой карты 300–550; synthesis 500–900; "
"practical_focus 180–350; reflection_question до 220; voice_summary 500–800 — отдельный "
"устный пересказ, не копия synthesis; share_summary 180–300 — итог для пересылки, "
"не упоминай вопрос пользователя."
)
FORMAT_EN = (
    "Return the result strictly as a JSON object with fields: headline, opening, "
    "card_interpretations (array of objects with fields: position, card_name, orientation, "
    "core_message, symbolic_detail, context_connection), synthesis, practical_focus, "
    "reflection_question, voice_summary, share_summary. "
    "All texts should be natural and flowing, without headings or bullet lists. Length guidance "
"in characters: headline up to 90; opening 120–250; each card interpretation 300–550; "
"synthesis 500–900; practical_focus 180–350; reflection_question up to 220; voice_summary "
"500–800 — a separate spoken summary, not a copy of synthesis; share_summary 180–300 — a "
"shareable takeaway, do not mention the user's question."
)


class CardInterpretation(BaseModel):
    position: str = Field(min_length=1, max_length=64)
    card_name: str = Field(min_length=1, max_length=64)
    orientation: str = Field(min_length=1, max_length=16)  # "upright" or "reversed"
    core_message: str = Field(min_length=300, max_length=550)  # 300-550 chars per card
    symbolic_detail: str = Field(min_length=0, max_length=200)
    context_connection: str = Field(min_length=0, max_length=200)


class TarotReadingResult(BaseModel):
    headline: str = Field(min_length=1, max_length=90)
    opening: str = Field(min_length=120, max_length=250)
    card_interpretations: list[CardInterpretation] = Field(min_length=1)
    synthesis: str = Field(min_length=500, max_length=900)
    practical_focus: str = Field(min_length=180, max_length=350)
    reflection_question: str = Field(min_length=1, max_length=220)
    voice_summary: str = Field(min_length=500, max_length=800)
    share_summary: str = Field(min_length=180, max_length=300)

    @model_validator(mode="after")
    def _voice_must_not_copy_synthesis(self) -> "TarotReadingResult":
        """voice_summary must be a separate spoken text, not a copy of synthesis."""
        voice = (self.voice_summary or "").strip().lower()
        synth = (self.synthesis or "").strip().lower()
        if voice and synth and (voice == synth or voice in synth or synth in voice):
            raise ValueError(
                "voice_summary must be a separate spoken summary, not a copy of synthesis"
            )
        return self


def assert_share_summary_privacy(share_summary: str, question: str | None) -> None:
    """Raise ValueError if the querent's private question leaks into share_summary.

    Best-effort guard: catches verbatim echoes of the question (the common leak);
    heavily paraphrased fragments still rely on the prompt rule and manual review.
    """
    q = (question or "").strip()
    if not q or q == "-":
        return
    if q.lower() in (share_summary or "").lower():
        raise ValueError("share_summary contains the querent's private question")


def _provider_from_url(base_url: str) -> str:
    try:
        return urlparse(base_url).netloc or base_url
    except Exception:  # noqa: BLE001
        return base_url


def _build_card_block(
    lang: str, card: DrawnCard, spread_id: str, include_symbols: bool = True
) -> str:
    """Build a structured description of a drawn card for the LLM prompt."""
    drawn = card
    label = drawn.position_label.get(lang, drawn.position_label["ru"])
    name = drawn.card.name(lang)
    pos_meaning = position_meaning(spread_id, drawn.position_id, lang)
    orientation = "перевёрнутая" if drawn.reversed else "прямая" if lang == "ru" else "reversed" if drawn.reversed else "upright"
    kws = ", ".join(drawn.card.keywords(lang))

    block = f"Позиция «{label}» (значение: {pos_meaning}). Карта: {name} ({orientation}). Ключевые темы: {kws}."
    if lang == "en":
        block = f"Position «{label}» (meaning: {pos_meaning}). Card: {name} ({orientation}). Key themes: {kws}."

    loc = drawn.card.localized(lang)
    if include_symbols:
        if loc.symbols:
            sym_str = ", ".join(loc.symbols[:3])
            if lang == "ru":
                block += f" Визуальные символы карты: {sym_str}."
            else:
                block += f" Visual symbols: {sym_str}."

    # Расширенные поля (light/shadow/advice) вытянутой ориентации
    cm = loc.reversed if drawn.reversed else loc.upright
    if cm.light:
        block += f" Дар: {cm.light}." if lang == "ru" else f" Gift: {cm.light}."
    if cm.shadow:
        block += f" Тень: {cm.shadow}." if lang == "ru" else f" Shadow: {cm.shadow}."
    if cm.advice:
        block += f" Действие: {cm.advice}." if lang == "ru" else f" Action: {cm.advice}."
    return block


def _build_user_message(
    lang: str,
    spread_id: str,
    spread_title: str,
    question: str | None,
    drawn: list[DrawnCard],
    memory: str,
) -> str:
    # Level 1: Voice
    parts = [VOICE_RU if lang == "ru" else VOICE_EN, ""]

    # Level 2: Spread rules
    rules = (SPREAD_RULES_RU if lang == "ru" else SPREAD_RULES_EN).get(spread_id, "")
    if rules:
        parts.append(rules)
        parts.append("")

    # Level 3: Card data
    if lang == "ru":
        parts.append(f"Расклад: {spread_title}")
    else:
        parts.append(f"Spread: {spread_title}")
    if question and question.strip() not in ("-", ""):
        if lang == "ru":
            parts.append(f"Вопрос спрашивающего: {question.strip()}")
        else:
            parts.append(f"Querent's question: {question.strip()}")
    parts.append("")
    if lang == "ru":
        parts.append("Карты в раскладе:")
    else:
        parts.append("Cards in the spread:")
    for d in drawn:
        parts.append("- " + _build_card_block(lang, d, spread_id))
    parts.append("")

    # Level 4: Memory
    if memory:
        if lang == "ru":
            parts.append(
                f"Контекст — недавние расклады спрашивающего (учти преемственность тем, не копируй дословно): {memory}"
            )
        else:
            parts.append(
                f"Context — the querent's recent readings (keep themes consistent, do not copy verbatim): {memory}"
            )
        parts.append("")

    # Level 5: Format
    parts.append(FORMAT_RU if lang == "ru" else FORMAT_EN)

    return "\n".join(parts)


async def _recent_reads_memory(user_id: int, limit: int = 3) -> str:
    """Return a short, privacy-safe memory snippet. Never includes Telegram IDs or usernames.

    When agent-core is available, the snippet is also written to MemoryStore
    with confidence and trust metadata, enabling cross-session long-term memory.
    """
    try:
        async with get_session() as session:
            rows = (
                await session.execute(
                    select(Reading.interpretation)
                    .where(Reading.user_id == user_id, Reading.interpretation.is_not(None))
                    .order_by(Reading.id.desc())
                    .limit(limit)
                )
            ).scalars().all()
        parts = [r[:300] for r in reversed(rows) if r]
        memory_text = " | ".join(parts)[:900]
    except Exception:  # noqa: BLE001
        return ""

    # --- agent-core: persist memory with confidence ---
    if _AGENT_CORE and memory_text:
        try:
            harness = get_harness()
            await harness.memory.put(
                f"user:{user_id}:recent_reads",
                memory_text,
                ttl=3600,  # 1 hour
                trust=TrustTier.MACHINE_CONFIRMED,
                confidence=0.8,
                actor="agent:moira",
                scope="session",
            )
        except Exception:  # noqa: BLE001
            pass  # memory store is best-effort

    return memory_text


def _error_category(exc: Exception) -> str:
    msg = str(exc).lower()
    if "timeout" in msg:
        return "timeout"
    if "truncat" in msg or "incomplete" in msg:
        return "truncation"
    if "validation" in msg or "json" in msg:
        return "validation"
    if "connect" in msg or "network" in msg:
        return "network"
    return "unknown"


async def _log_usage(
    *,
    user_id: int,
    spread: str | None,
    model: str | None,
    provider: str,
    status: str,
    latency_ms: int,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    attempts: int = 0,
    fallback_used: bool = False,
    error_category: str | None = None,
) -> None:
    try:
        async with get_session() as session:
            session.add(
                LlmUsage(
                    user_id=user_id,
                    spread=spread,
                    model=model,
                    prompt_version=PROMPT_VERSION,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    status=status,
                )
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_usage log failed: %s", exc)

    # --- agent-core: record evidence ---
    if _AGENT_CORE:
        try:
            chain = get_evidence()
            chain.add(
                EvidenceRecord(
                    id=f"llm:{user_id}:{int(datetime.now().timestamp())}",
                    action=f"llm_interpret status={status} spread={spread}",
                    actor="agent:moira",
                    timestamp=datetime.now(),
                    inputs={
                        "user_id": user_id,
                        "spread": spread,
                        "model": model,
                        "provider": provider,
                        "attempts": attempts,
                    },
                    outputs={
                        "status": status,
                        "latency_ms": latency_ms,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "fallback_used": fallback_used,
                        "error_category": error_category,
                    },
                    success=(status == "ok"),
                    error=error_category if status != "ok" else None,
                )
            )
        except Exception:  # noqa: BLE001
            pass  # evidence chain is best-effort

    logger.debug(
        "llm_usage provider=%s attempts=%d fallback=%s error_category=%s",
        provider, attempts, fallback_used, error_category,
    )


async def interpret_reading(
    cfg: Config,
    lang: str,
    spread_title: str,
    question: str | None,
    drawn: list[DrawnCard],
    user_id: int | None = None,
    spread_id: str | None = None,
) -> TarotReadingResult | None:
    """Return structured LLM interpretation or None when unavailable/failed (fallback path).

    Policy: one primary request + at most one format/network retry, then fallback.
    Instructor's own retries are disabled to avoid nested retry loops.
    """
    if not cfg.openrouter_api_key:
        return None
    try:
        import instructor
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("instructor/openai missing — falling back to embedded meanings")
        return None

    # --- agent-core: attention transition → FOCUS ---
    if _AGENT_CORE:
        try:
            attn = get_attention()
            attn.transition(AttentionState.FOCUS, reason=f"interpret_reading: {spread_id}")
        except Exception:  # noqa: BLE001
            pass

    provider = _provider_from_url(cfg.llm_base_url)
    memory = await _recent_reads_memory(user_id) if user_id else ""
    user_message = _build_user_message(lang, spread_id or "", spread_title, question, drawn, memory)
    messages = [
        {"role": "system", "content": "You are Moira, a tarot oracle. Follow the user's instructions exactly."},
        {"role": "user", "content": user_message},
    ]
    client = instructor.from_openai(
        AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key, timeout=90.0)
    )
    create_fn = getattr(client.chat.completions, "create_with_completion", None)

    started = time.monotonic()
    last_exc: Exception | None = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            if create_fn is not None:
                result, completion = await create_fn(
                    model=cfg.llm_model,
                    response_model=TarotReadingResult,
                    max_retries=0,
                    temperature=0.8,
                    max_tokens=2000,
                    messages=messages,
                )
            else:
                result = await client.chat.completions.create(
                    model=cfg.llm_model,
                    response_model=TarotReadingResult,
                    max_retries=0,
                    temperature=0.8,
                    max_tokens=2000,
                    messages=messages,
                )
                completion = None
            if len(result.card_interpretations) != len(drawn):
                logger.warning(
                    "LLM returned %d interpretations for %d cards (attempt %d)",
                    len(result.card_interpretations), len(drawn), attempt,
                )
                last_exc = ValueError(f"interpretation count mismatch: {len(result.card_interpretations)} != {len(drawn)}")
                continue
            if question:
                try:
                    assert_share_summary_privacy(result.share_summary, question)
                except ValueError as privacy_exc:
                    logger.warning("share_summary leaks the user question (attempt %d)", attempt)
                    last_exc = privacy_exc
                    continue
            latency = int((time.monotonic() - started) * 1000)
            usage = getattr(completion, "usage", None) if completion is not None else None
            await _log_usage(
                user_id=user_id or 0,
                spread=spread_id,
                model=cfg.llm_model,
                provider=provider,
                status="ok",
                latency_ms=latency,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                attempts=attempt,
                fallback_used=False,
                error_category=None,
            )
            # --- agent-core: attention transition → IDLE (success) ---
            if _AGENT_CORE:
                try:
                    get_attention().transition(AttentionState.IDLE, reason="llm success")
                except Exception:  # noqa: BLE001
                    pass
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("LLM request failed (attempt %d): %s", attempt, exc)

    latency = int((time.monotonic() - started) * 1000)
    await _log_usage(
        user_id=user_id or 0,
        spread=spread_id,
        model=cfg.llm_model,
        provider=provider,
        status="fallback",
        latency_ms=latency,
        attempts=MAX_LLM_ATTEMPTS,
        fallback_used=True,
        error_category=_error_category(last_exc) if last_exc else None,
    )
    # --- agent-core: attention transition → IDLE (fallback) ---
    if _AGENT_CORE:
        try:
            get_attention().transition(AttentionState.IDLE, reason="llm fallback")
        except Exception:  # noqa: BLE001
            pass
    return None


async def weekly_mirror_text(cfg: Config, lang: str, top_cards: list[str], readings_count: int) -> str | None:
    """Short weekly reflection built from the user's top cards. Returns plain text or None."""
    if not cfg.openrouter_api_key or not top_cards:
        return None
    try:
        import instructor
        from openai import AsyncOpenAI
    except ImportError:
        return None

    class MirrorResult(BaseModel):
        summary: str = Field(min_length=1, max_length=600)
        question: str = Field(min_length=1, max_length=250)

    system = (
        "Ты — Мойра, спокойный таро-оракул. Кратко (до 5 предложений) и тепло подведи итог недели "
        "человека по выпавшим картам: общая тема недели и один глубокий вопрос для размышления. "
        "Без предсказаний и гарантий. Язык ответа: русский."
        if lang == "ru"
        else
        "You are Moira, a calm tarot oracle. Briefly (max 5 sentences) and warmly summarise the "
        "person's week from the cards drawn: the week's overall theme and one deep reflection "
        "question. No predictions or guarantees. Answer in English."
    )
    user_msg = (
        f"За неделю сделано раскладов: {readings_count}. Чаще всего выпадали карты: "
        if lang == "ru"
        else f"Readings this week: {readings_count}. Most frequent cards: "
    ) + ", ".join(top_cards)
    client = instructor.from_openai(
        AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key, timeout=60.0)
    )
    try:
        result = await client.chat.completions.create(
            model=cfg.llm_model,
            response_model=MirrorResult,
            max_retries=0,
            temperature=0.7,
            max_tokens=500,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        )
        return f"{result.summary}\n\n✦ {result.question}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("mirror LLM failed: %s", exc)
        return None
