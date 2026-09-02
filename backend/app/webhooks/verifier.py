import hashlib
import hmac


def verify_signature(
    raw_body: bytes,
    received_signature: str,
    webhook_secret: str,
) -> bool:
    """
    Verify a Razorpay webhook signature.

    raw_body must be the exact bytes received from the request.
    """

    if not received_signature or not webhook_secret:
        return False

    expected_signature = hmac.new(
        key=webhook_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        received_signature,
    )