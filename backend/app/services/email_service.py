import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        """
        Sends email using configured provider abstraction (mock, smtp, resend).
        Does not crash or depend on external APIs if unconfigured.
        """
        if not to_email:
            return False

        if settings.EMAIL_PROVIDER == "smtp" and settings.SMTP_HOST and settings.SMTP_USER:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = to_email

                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)
                if body_html:
                    part2 = MIMEText(body_html, "html")
                    msg.attach(part2)

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
                    server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
                
                logger.info(f"SMTP email sent to {to_email}: {subject}")
                return True
            except Exception as e:
                logger.error(f"Failed to send SMTP email: {e}")
                return False

        elif settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": settings.EMAIL_FROM,
                            "to": [to_email],
                            "subject": subject,
                            "text": body_text,
                            "html": body_html or f"<p>{body_text}</p>"
                        }
                    )
                    if response.status_code in [200, 201]:
                        logger.info(f"Resend email sent to {to_email}")
                        return True
                    else:
                        logger.error(f"Resend email error: {response.text}")
                        return False
            except Exception as e:
                logger.error(f"Failed to send Resend email: {e}")
                return False

        # Default Mock mode
        logger.info(f"[MOCK EMAIL DISPATCH] To: {to_email} | Subject: {subject} | Content: {body_text[:100]}...")
        return True
