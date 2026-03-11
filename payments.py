"""Telegram Stars payment utilities — single source of truth for prices and helpers."""
from aiogram.types import LabeledPrice

# ── Stars prices (in ⭐) per subject per duration ──────────────────────────
STARS_PRICES: dict[int, int] = {
    30: 300,
    90: 750,
    180: 1200,
}

# ── YooMoney prices (in ₽) per duration ───────────────────────────────────
YOOMONEY_PRICES: dict[int, int] = {
    30: 200,
    90: 500,
    180: 900,
}

# ── Stars prices used when gifting a subscription ─────────────────────────
GIFT_STARS_PRICES: dict[int, int] = {
    7: 100,
    30: 300,
    90: 750,
}


def make_stars_invoice_prices(days: int) -> list[LabeledPrice]:
    """Return a one-element LabeledPrice list suitable for send_invoice (XTR)."""
    return [LabeledPrice(label=f"{days} дней", amount=STARS_PRICES[days])]


def build_stars_payload(subject: str, days: int, order_id: str) -> str:
    """Encode invoice payload as ``<order_id>:<subject>:<days>``."""
    return f"{order_id}:{subject}:{days}"


def parse_stars_payload(payload: str) -> tuple[str, str, int] | None:
    """Parse payload produced by :func:`build_stars_payload`.

    Returns ``(order_id, subject, days)`` on success, ``None`` on any error.
    """
    try:
        order_id, subject, days_str = payload.split(":", 2)
        return order_id, subject, int(days_str)
    except (ValueError, AttributeError):
        return None