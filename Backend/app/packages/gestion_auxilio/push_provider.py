from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings


settings = get_settings()
_firebase_app = None


class PushProviderError(RuntimeError):
    """Raised when push delivery cannot be completed."""


@dataclass(frozen=True)
class PushDispatchResult:
    provider: str
    sent_count: int
    failed_count: int
    invalid_tokens: tuple[str, ...] = ()
    detail: str | None = None

    @property
    def success(self) -> bool:
        return self.sent_count > 0


def _send_sandbox_push(
    *,
    device_tokens: list[str],
    title: str,
    message: str,
    payload: dict[str, object] | None,
) -> PushDispatchResult:
    del title, message, payload

    invalid_tokens = tuple(
        token
        for token in device_tokens
        if "invalid" in token.strip().lower()
    )
    sent_count = len(device_tokens) - len(invalid_tokens)
    failed_count = len(invalid_tokens)
    detail = None
    if sent_count == 0 and failed_count > 0:
        detail = "All device tokens were rejected by the sandbox provider."
    return PushDispatchResult(
        provider="sandbox",
        sent_count=sent_count,
        failed_count=failed_count,
        invalid_tokens=invalid_tokens,
        detail=detail,
    )


def _get_firebase_app(credentials_file: Path):
    global _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:
        raise PushProviderError(
            "FCM provider is configured but firebase_admin is not installed."
        ) from exc

    if _firebase_app is None:
        if not credentials_file.exists():
            raise PushProviderError("FCM credentials file is not available.")
        _firebase_app = firebase_admin.initialize_app(
            credentials.Certificate(str(credentials_file))
        )
    return _firebase_app


def _send_fcm_push(
    *,
    device_tokens: list[str],
    title: str,
    message: str,
    payload: dict[str, object] | None,
) -> PushDispatchResult:
    credentials_file = settings.fcm_credentials_file
    if credentials_file is None:
        raise PushProviderError("FCM provider is configured but credentials are missing.")

    app = _get_firebase_app(credentials_file)

    try:
        from firebase_admin import messaging
    except ImportError as exc:
        raise PushProviderError(
            "FCM provider is configured but firebase_admin messaging is unavailable."
        ) from exc

    message_data = {
        key: str(value)
        for key, value in (payload or {}).items()
        if value is not None
    }
    multicast_message = messaging.MulticastMessage(
        tokens=device_tokens,
        notification=messaging.Notification(title=title, body=message),
        data=message_data,
    )
    batch_response = messaging.send_each_for_multicast(multicast_message, app=app)

    invalid_codes = {
        "registration-token-not-registered",
        "invalid-registration-token",
    }
    invalid_tokens: list[str] = []
    for token, response in zip(device_tokens, batch_response.responses):
        if response.success:
            continue
        if response.exception is None:
            continue
        code = getattr(response.exception, "code", None)
        if code in invalid_codes:
            invalid_tokens.append(token)

    return PushDispatchResult(
        provider="fcm",
        sent_count=batch_response.success_count,
        failed_count=batch_response.failure_count,
        invalid_tokens=tuple(invalid_tokens),
        detail=None if batch_response.success_count else "FCM provider did not accept any token.",
    )


def send_push_notification(
    *,
    device_tokens: list[str],
    title: str,
    message: str,
    payload: dict[str, object] | None,
) -> PushDispatchResult:
    if not device_tokens:
        return PushDispatchResult(
            provider=settings.push_provider,
            sent_count=0,
            failed_count=0,
            detail="No device tokens were available for dispatch.",
        )

    provider = settings.push_provider.strip().lower()
    if provider == "sandbox":
        return _send_sandbox_push(
            device_tokens=device_tokens,
            title=title,
            message=message,
            payload=payload,
        )
    if provider == "fcm":
        return _send_fcm_push(
            device_tokens=device_tokens,
            title=title,
            message=message,
            payload=payload,
        )
    raise PushProviderError(f"Unsupported push provider: {settings.push_provider}")
