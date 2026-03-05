"""
smtp_service.py
SMTP/IMAP backend for Outlook Smart Reminder System.

Compatible with Gmail (App Password), Outlook.com personal,
and any standard SMTP/IMAP provider.

Provides the same interface as OutlookService so the rest of
the app works without changes.
"""
import imaplib
import logging
import re
import smtplib
import email as email_lib
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, parsedate_to_datetime

logger = logging.getLogger(__name__)

# Regex patterns for response label detection (Spanish + English)
LABEL_PATTERNS = [
    (re.compile(r"contestar\s+despu[eé]s\s+de\s+(\d+)\s*d[ií]a", re.I), "days"),
    (re.compile(r"reply\s+in\s+(\d+)\s*day", re.I), "days"),
    (re.compile(r"respond\s+in\s+(\d+)\s*day", re.I), "days"),
    (re.compile(r"(\d+)\s*day[s]?\s+(later|after|from now)", re.I), "days"),
    (re.compile(r"al\s+final\s+del\s+d[ií]a", re.I), "end_of_day"),
    (re.compile(r"end\s+of\s+(the\s+)?day", re.I), "end_of_day"),
    (re.compile(r"\bmañana\b", re.I), "tomorrow"),
    (re.compile(r"\btomorrow\b", re.I), "tomorrow"),
]


def _strip_html(html: str) -> str:
    """Remove HTML tags to get plain text."""
    return re.sub(r"<[^>]+>", " ", html)


class SMTPService:
    """
    SMTP/IMAP email service.

    Provides send_email, has_reply, detect_response_labels, sync_contacts
    with the same interface as OutlookService.
    """

    def __init__(self, smtp_host: str, smtp_port: int, imap_host: str, imap_port: int,
                 username: str, password: str, sender_email: str = None):
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.imap_host = imap_host
        self.imap_port = int(imap_port)
        self.username = username
        self.password = password
        self.sender_email = sender_email or username

    def _smtp_connect(self):
        """
        Open and authenticate an SMTP connection.
        Tries STARTTLS (port 587) first, then SSL (port 465) as fallback.
        Updates self.smtp_port to whichever method works.
        """
        import socket

        def _try_starttls(port):
            s = smtplib.SMTP(self.smtp_host, port, timeout=20)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(self.username, self.password)
            return s

        def _try_ssl(port):
            s = smtplib.SMTP_SSL(self.smtp_host, port, timeout=20)
            s.login(self.username, self.password)
            return s

        # Build attempt list: try configured port first, then the other
        if self.smtp_port == 465:
            attempts = [(465, _try_ssl), (587, _try_starttls)]
        else:
            attempts = [(587, _try_starttls), (465, _try_ssl)]

        last_err = None
        for port, method in attempts:
            try:
                conn = method(port)
                self.smtp_port = port  # remember what worked
                return conn
            except smtplib.SMTPAuthenticationError:
                raise  # don't retry — wrong password
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                last_err = e
                logger.debug("SMTP %s:%s failed (%s), trying next…", self.smtp_host, port, e)
                continue

        raise ConnectionError(
            f"No se pudo conectar a {self.smtp_host} en ningún puerto (587/465). "
            "Comprueba que:\n"
            "  1. Tu red/firewall permite conexiones SMTP salientes\n"
            "  2. SMTP AUTH está habilitado para tu cuenta en Office 365\n"
            f"  Último error técnico: {last_err}"
        )

    # ── Connection ─────────────────────────────────────────────────────────────

    def validate_connection(self):
        """Test SMTP login. Returns (ok: bool, message: str)."""
        try:
            s = self._smtp_connect()
            s.quit()
            return True, f"Conexión exitosa como {self.sender_email} (puerto {self.smtp_port})"
        except smtplib.SMTPAuthenticationError:
            return False, (
                "Credenciales incorrectas. "
                "Si tu cuenta tiene verificación en dos pasos activa, genera una "
                "contraseña de aplicación en account.microsoft.com en lugar de usar "
                "tu contraseña habitual."
            )
        except ConnectionError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, f"Error inesperado: {exc}"

    def _imap_connect(self):
        """Return an authenticated imaplib.IMAP4_SSL connection."""
        mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        mail.login(self.username, self.password)
        return mail

    # ── Sending ────────────────────────────────────────────────────────────────

    def send_email(self, to_email: str, subject: str, body_html: str,
                   body_text: str = "", category: str = None,
                   in_reply_to: str = None, references: str = None) -> dict:
        """
        Send an email via SMTP.

        Returns dict with message_id and conversation_id.
        For threading, message_id is used as conversation_id in SMTP mode.
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to_email
        msg["Message-ID"] = make_msgid(domain=self.sender_email.split("@")[-1])
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = references or in_reply_to
        if category:
            msg["X-Category"] = category

        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        s = self._smtp_connect()
        try:
            s.send_message(msg)
        finally:
            try:
                s.quit()
            except Exception:
                pass

        message_id = msg["Message-ID"]
        logger.info("Email sent to %s — Message-ID: %s", to_email, message_id)
        return {
            "message_id": message_id,
            "conversation_id": message_id,  # use message_id as thread anchor
            "graph_id": "",
        }

    # ── Reply detection ────────────────────────────────────────────────────────

    def has_reply(self, conversation_id: str, sent_at: datetime) -> bool:
        """
        Check IMAP INBOX for a reply to the given message_id after sent_at.

        conversation_id is the Message-ID stored at send time.
        Looks for messages with In-Reply-To or References header matching it.
        """
        try:
            mail = self._imap_connect()
            mail.select("INBOX")
            since_str = (sent_at - timedelta(days=1)).strftime("%d-%b-%Y")
            # Search by In-Reply-To header
            clean_id = conversation_id.strip("<>")
            _, data = mail.search(None, f'SINCE "{since_str}" HEADER "In-Reply-To" "<{clean_id}>"')
            found = bool(data[0].split())
            if not found:
                # Fallback: search References
                _, data = mail.search(None, f'SINCE "{since_str}" HEADER "References" "<{clean_id}>"')
                found = bool(data[0].split())
            mail.logout()
            return found
        except Exception as exc:
            logger.error("IMAP has_reply error: %s", exc)
            return False

    def detect_response_labels(self, conversation_id: str, sent_at: datetime):
        """
        Scan reply bodies for scheduling labels.

        Returns a label string like '2_days', 'end_of_day', 'tomorrow' or None.
        """
        try:
            mail = self._imap_connect()
            mail.select("INBOX")
            since_str = (sent_at - timedelta(days=1)).strftime("%d-%b-%Y")
            clean_id = conversation_id.strip("<>")
            _, data = mail.search(None, f'SINCE "{since_str}" HEADER "In-Reply-To" "<{clean_id}>"')
            ids = data[0].split()
            if not ids:
                _, data = mail.search(None, f'SINCE "{since_str}" HEADER "References" "<{clean_id}>"')
                ids = data[0].split()
            label = None
            for num in ids:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                text = _get_body_text(msg)
                label = _detect_label(text)
                if label:
                    break
            mail.logout()
            return label
        except Exception as exc:
            logger.error("IMAP detect_labels error: %s", exc)
            return None

    # ── Contacts (not available in SMTP mode) ──────────────────────────────────

    def sync_contacts(self):
        """IMAP does not provide contact lists. Returns empty list."""
        logger.info("sync_contacts: SMTP backend — no contact sync available")
        return []

    def ensure_category_exists(self, name: str, color: str):
        """No-op for SMTP mode (Outlook categories not applicable)."""
        pass

    def get_master_categories(self):
        return []


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_body_text(msg) -> str:
    """Extract plain text body from an email.Message object."""
    text_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    text_parts.append(part.get_payload(decode=True).decode("utf-8", errors="ignore"))
                except Exception:
                    pass
            elif ct == "text/html" and not text_parts:
                try:
                    html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    text_parts.append(_strip_html(html))
                except Exception:
                    pass
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            raw = payload.decode("utf-8", errors="ignore")
            if msg.get_content_type() == "text/html":
                text_parts.append(_strip_html(raw))
            else:
                text_parts.append(raw)
    return " ".join(text_parts)


def _detect_label(text: str):
    """Apply label patterns to text. Returns label string or None."""
    for pattern, kind in LABEL_PATTERNS:
        m = pattern.search(text)
        if m:
            if kind == "days":
                n = int(m.group(1)) if m.lastindex else 1
                return f"{n}_day" if n == 1 else f"{n}_days"
            return kind
    return None
