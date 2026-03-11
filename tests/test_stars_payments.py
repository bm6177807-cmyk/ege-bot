"""Unit tests for Telegram Stars payment helpers and DB idempotency."""
import sys
import os
import sqlite3
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db
from payments import (
    STARS_PRICES,
    GIFT_STARS_PRICES,
    YOOMONEY_PRICES,
    build_stars_payload,
    parse_stars_payload,
    make_stars_invoice_prices,
)


# ---------------------------------------------------------------------------
# payments.py helpers
# ---------------------------------------------------------------------------
class TestParseStarsPayload:
    def test_roundtrip(self):
        """build_stars_payload → parse_stars_payload must be lossless."""
        order_id = "550e8400-e29b-41d4-a716-446655440000"
        result = parse_stars_payload(build_stars_payload("chemistry", 30, order_id))
        assert result == (order_id, "chemistry", 30)

    def test_all_subjects_and_durations(self):
        for subject in ("chemistry", "biology", "math", "physics", "social"):
            for days in (30, 90, 180):
                oid = f"oid-{subject}-{days}"
                r = parse_stars_payload(build_stars_payload(subject, days, oid))
                assert r == (oid, subject, days), f"Failed for {subject}/{days}"

    def test_bad_payload_returns_none(self):
        assert parse_stars_payload("") is None
        assert parse_stars_payload("no_colons") is None
        assert parse_stars_payload("a:b:notanint") is None

    def test_legacy_payload_not_parsed_by_parser(self):
        """Old-format 'subject:days' payloads are NOT valid for the new parser."""
        assert parse_stars_payload("chemistry:30") is None


class TestStarsPrices:
    def test_prices_are_positive(self):
        for days, price in STARS_PRICES.items():
            assert price > 0, f"STARS_PRICES[{days}] must be > 0"

    def test_gift_prices_positive(self):
        for days, price in GIFT_STARS_PRICES.items():
            assert price > 0

    def test_yoomoney_prices_positive(self):
        for days, price in YOOMONEY_PRICES.items():
            assert price > 0

    def test_make_invoice_prices_returns_list(self):
        prices = make_stars_invoice_prices(30)
        assert len(prices) == 1
        assert prices[0].amount == STARS_PRICES[30]

    def test_longer_durations_cost_more_stars(self):
        assert STARS_PRICES[30] < STARS_PRICES[90] < STARS_PRICES[180]


# ---------------------------------------------------------------------------
# database.py — Stars payment persistence & idempotency
# ---------------------------------------------------------------------------
class TestStarsPaymentDB:
    """These tests use an isolated in-memory SQLite DB via a temp file."""

    def _setup(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        old_path = db.DB_PATH
        db.DB_PATH = path
        db.init_db()
        return path, old_path

    def _teardown(self, path, old_path):
        db.DB_PATH = old_path
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_save_and_check_idempotency(self):
        path, old = self._setup()
        try:
            inserted = db.save_stars_payment(
                order_id="order-001",
                user_id=123,
                subject="chemistry",
                days=30,
                telegram_charge_id="tg-charge-abc",
            )
            assert inserted is True
            assert db.is_stars_payment_exists("tg-charge-abc") is True
        finally:
            self._teardown(path, old)

    def test_duplicate_telegram_charge_id_rejected(self):
        path, old = self._setup()
        try:
            db.save_stars_payment(
                order_id="order-001",
                user_id=123,
                subject="chemistry",
                days=30,
                telegram_charge_id="tg-charge-dup",
            )
            second = db.save_stars_payment(
                order_id="order-002",
                user_id=123,
                subject="chemistry",
                days=30,
                telegram_charge_id="tg-charge-dup",
            )
            assert second is False
        finally:
            self._teardown(path, old)

    def test_unknown_charge_id_returns_false(self):
        path, old = self._setup()
        try:
            assert db.is_stars_payment_exists("nonexistent-charge-id") is False
        finally:
            self._teardown(path, old)

    def test_different_users_same_subject_idempotent(self):
        path, old = self._setup()
        try:
            r1 = db.save_stars_payment("o1", 111, "math", 90, "charge-111")
            r2 = db.save_stars_payment("o2", 222, "math", 90, "charge-222")
            assert r1 is True
            assert r2 is True
        finally:
            self._teardown(path, old)


if __name__ == "__main__":
    suites = [
        TestParseStarsPayload,
        TestStarsPrices,
        TestStarsPaymentDB,
    ]
    total = passed = 0
    for cls in suites:
        instance = cls()
        for method in [m for m in dir(instance) if m.startswith("test_")]:
            total += 1
            try:
                getattr(instance, method)()
                print(f"  PASS  {cls.__name__}.{method}")
                passed += 1
            except Exception as exc:
                print(f"  FAIL  {cls.__name__}.{method}: {exc}")
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
