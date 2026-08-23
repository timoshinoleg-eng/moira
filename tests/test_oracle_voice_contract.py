from bot.llm.adapter import VOICE_EN, VOICE_RU


def test_ru_oracle_voice_is_mystical_but_not_deterministic() -> None:
    assert "порог" in VOICE_RU
    assert "вероятное движение" in VOICE_RU
    assert "не обещай судьбу" in VOICE_RU


def test_en_oracle_voice_is_mystical_but_not_deterministic() -> None:
    assert "threshold" in VOICE_EN
    assert "likely movement" in VOICE_EN
    assert "never promise fate" in VOICE_EN
