from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: str
    kind: str  # readings | days
    amount: int
    xtr: int  # price in Telegram Stars
    subscription: bool = False


PRODUCTS: dict[str, Product] = {
    "reading_1": Product("reading_1", "readings", 1, 25),
    "unlimited_7": Product("unlimited_7", "days", 7, 99),
    "unlimited_30": Product("unlimited_30", "days", 30, 150, subscription=True),
}

PAYLOAD_PREFIX = "moira"


def payload_for(product_id: str) -> str:
    return f"{PAYLOAD_PREFIX}:{product_id}"


def parse_payload(payload: str) -> Product | None:
    parts = payload.split(":")
    if len(parts) == 2 and parts[0] == PAYLOAD_PREFIX and parts[1] in PRODUCTS:
        return PRODUCTS[parts[1]]
    return None
