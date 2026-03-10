"""Unit tests for YooMoney SHA-1 signature verification."""
import hashlib
import hmac
import sys
import os

# Allow importing bot.py helpers without running the full application
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _verify_yoomoney_signature(data: dict, secret: str) -> bool:
    """Replicated from bot.py for isolated testing."""
    string_to_hash = "&".join([
        data.get("notification_type", ""),
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        secret,
        data.get("label", ""),
    ])
    expected = hashlib.sha1(string_to_hash.encode("utf-8")).hexdigest()
    received = data.get("sha1_hash", "")
    return hmac.compare_digest(expected, received)


def _make_notification(secret: str, **overrides) -> dict:
    """Build a minimal YooMoney notification dict with a valid sha1_hash."""
    base = {
        "notification_type": "p2p-incoming",
        "operation_id": "12345678",
        "amount": "200.00",
        "currency": "643",
        "datetime": "2026-03-10T22:00:00.000+03:00",
        "sender": "",
        "codepro": "false",
        "label": "order-test-uuid",
    }
    base.update(overrides)
    # Compute and attach the correct sha1_hash
    string_to_hash = "&".join([
        base["notification_type"],
        base["operation_id"],
        base["amount"],
        base["currency"],
        base["datetime"],
        base["sender"],
        base["codepro"],
        secret,
        base["label"],
    ])
    base["sha1_hash"] = hashlib.sha1(string_to_hash.encode("utf-8")).hexdigest()
    return base


class TestVerifyYoomoneySignature:
    def test_valid_signature_passes(self):
        secret = "my-secret-word"
        data = _make_notification(secret)
        assert _verify_yoomoney_signature(data, secret) is True

    def test_wrong_secret_fails(self):
        data = _make_notification("correct-secret")
        assert _verify_yoomoney_signature(data, "wrong-secret") is False

    def test_tampered_amount_fails(self):
        secret = "my-secret-word"
        data = _make_notification(secret)
        data["amount"] = "999.00"  # tamper after signing
        assert _verify_yoomoney_signature(data, secret) is False

    def test_missing_sha1_hash_fails(self):
        secret = "my-secret-word"
        data = _make_notification(secret)
        data.pop("sha1_hash")
        assert _verify_yoomoney_signature(data, secret) is False

    def test_empty_secret_allowed(self):
        """When secret is empty string the hash is still computed (no exception)."""
        secret = ""
        data = _make_notification(secret)
        assert _verify_yoomoney_signature(data, secret) is True

    def test_cyrillic_label_works(self):
        secret = "тест-секрет"
        data = _make_notification(secret, label="заказ-123")
        assert _verify_yoomoney_signature(data, secret) is True


if __name__ == "__main__":
    # Run without pytest if needed
    suite = TestVerifyYoomoneySignature()
    tests = [m for m in dir(suite) if m.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            getattr(suite, t)()
            print(f"  PASS  {t}")
        except AssertionError as e:
            print(f"  FAIL  {t}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(failed)
