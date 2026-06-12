from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import get_settings

log = logging.getLogger(__name__)


def _build_reset_email_html(
    to_email: str,
    reset_link: str,
    frontend_url: str,
    token: str,
) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
          <tr>
            <td style="padding:32px 32px 16px;text-align:center;">
              <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1a1a2e;">Recuperaci&oacute;n de contrase&ntilde;a</h1>
              <p style="margin:0;font-size:14px;color:#6b7280;">Haz clic en el bot&oacute;n para restablecer tu contrase&ntilde;a.</p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px;text-align:center;">
              <a href="{reset_link}" target="_blank" style="display:inline-block;padding:14px 36px;background-color:#2563eb;color:#ffffff;text-decoration:none;border-radius:8px;font-size:15px;font-weight:600;letter-spacing:0.3px;">
                Restablecer contrase&ntilde;a
              </a>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 16px;text-align:center;">
              <p style="margin:0;font-size:13px;color:#9ca3af;">O copia este enlace en tu navegador:</p>
              <p style="margin:4px 0 0;font-size:12px;word-break:break-all;color:#6b7280;">
                <a href="{reset_link}" target="_blank" style="color:#2563eb;">{reset_link}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 16px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#9ca3af;">
                Token de recuperaci&oacute;n (v&aacute;lido por 30 minutos):
              </p>
              <code style="display:inline-block;margin-top:4px;padding:8px 16px;background-color:#f3f4f6;border-radius:6px;font-size:12px;color:#374151;font-family:monospace;">
                {token}
              </code>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 24px;text-align:center;border-top:1px solid #e5e7eb;">
              <p style="margin:0;font-size:12px;color:#9ca3af;">
                SI2 Auxilio &mdash; {frontend_url}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_reset_password_email(
    to_email: str,
    reset_token: str,
    *,
    frontend_url: str | None = None,
) -> bool:
    settings = get_settings()
    base_url = (frontend_url or settings.frontend_url).rstrip("/")
    reset_link = f"{base_url}/reset-password?token={reset_token}"

    html = _build_reset_email_html(
        to_email=to_email,
        reset_link=reset_link,
        frontend_url=base_url,
        token=reset_token,
    )

    if not settings.smtp_username or not settings.smtp_password:
        log.warning(
            "SMTP not configured (SMTP_USERNAME / SMTP_PASSWORD missing). "
            "Reset email NOT sent to %s. Token: %s",
            to_email,
            reset_token,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    msg["To"] = to_email
    msg["Subject"] = "Recuperación de contraseña - SI2 Auxilio"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.sendmail(settings.email_from_address, [to_email], msg.as_string())
        server.quit()
        log.info("Reset password email sent to %s", to_email)
        return True
    except smtplib.SMTPException as exc:
        log.error("Failed to send email to %s: %s", to_email, exc)
        return False
    except OSError as exc:
        log.error("SMTP connection error for %s: %s", to_email, exc)
        return False
