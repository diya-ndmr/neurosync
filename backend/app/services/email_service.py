import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import settings


class EmailDeliveryError(Exception):
    pass


def _send_email(recipient: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        raise EmailDeliveryError("Resend API key is not configured")

    payload = json.dumps(
        {
            "from": settings.resend_from_email,
            "to": [recipient],
            "subject": subject,
            "html": html,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise EmailDeliveryError(f"Resend returned HTTP {response.status}")
    except HTTPError as error:
        raise EmailDeliveryError(f"Resend returned HTTP {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise EmailDeliveryError("Could not connect to Resend") from error


def send_password_reset_email(recipient: str, reset_url: str) -> None:
    _send_email(
        recipient,
        "Reset your NeuroSync password",
        (
            "<p>We received a request to reset your NeuroSync password.</p>"
            f'<p><a href="{reset_url}">Reset your password</a></p>'
            "<p>This link expires in 30 minutes. If you did not request this, "
            "you can ignore this email.</p>"
        ),
    )


def send_verification_email(recipient: str, verification_url: str) -> None:
    _send_email(
        recipient,
        "Confirm your NeuroSync email",
        (
            "<p>Confirm your email address to finish creating your NeuroSync account.</p>"
            f'<p><a href="{verification_url}">Confirm email address</a></p>'
            "<p>This link expires in 24 hours. If you did not create this account, "
            "you can ignore this email.</p>"
        ),
    )
