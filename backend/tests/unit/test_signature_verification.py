import hashlib
import hmac

from app.webhooks.verifier import verify_signature


WEBHOOK_SECRET = "test_secret_12345"


def _sign(raw_body: bytes, secret: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()


def test_valid_signature_is_accepted():
    body = b'{"event":"payment.failed","payload":{}}'

    signature = _sign(body, WEBHOOK_SECRET)

    assert verify_signature(
        body,
        signature,
        WEBHOOK_SECRET,
    ) is True


def test_invalid_signature_is_rejected():
    body = b'{"event":"payment.failed","payload":{}}'

    wrong_signature = _sign(
        body,
        "a_completely_different_secret",
    )

    assert verify_signature(
        body,
        wrong_signature,
        WEBHOOK_SECRET,
    ) is False


def test_missing_signature_is_rejected():
    body = b'{"event":"payment.failed","payload":{}}'

    assert verify_signature(
        body,
        "",
        WEBHOOK_SECRET,
    ) is False

    assert verify_signature(
        body,
        None,
        WEBHOOK_SECRET,
    ) is False


def test_tampered_body_is_rejected():
    body = b'{"event":"payment.failed","payload":{}}'

    signature = _sign(
        body,
        WEBHOOK_SECRET,
    )

    tampered_body = (
        b'{"event":"payment.failed",'
        b'"payload":{"amount":999999}}'
    )

    assert verify_signature(
        tampered_body,
        signature,
        WEBHOOK_SECRET,
    ) is False


def test_missing_secret_is_rejected():
    body = b'{"event":"payment.failed","payload":{}}'

    signature = _sign(
        body,
        WEBHOOK_SECRET,
    )

    assert verify_signature(
        body,
        signature,
        "",
    ) is False