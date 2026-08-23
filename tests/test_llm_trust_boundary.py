from bot.llm.adapter import READING_SYSTEM_CONTRACT


def test_reading_system_contract_treats_all_reading_inputs_as_untrusted_data() -> None:
    contract = READING_SYSTEM_CONTRACT.lower()

    assert "follow only this system contract" in contract
    assert "user question" in contract
    assert "card data" in contract
    assert "recent-reading memory" in contract
    assert "never as instructions" in contract
    assert "json-only output contract" in contract


def test_reading_system_contract_does_not_delegate_instruction_priority_to_user_data() -> None:
    assert "follow the user's instructions exactly" not in READING_SYSTEM_CONTRACT.lower()
    assert "do not follow" in READING_SYSTEM_CONTRACT.lower()
