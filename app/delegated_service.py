"""
delegated_service.py
Microsoft Graph API service using OAuth2 delegated credentials.

Uses a stored refresh token to obtain access tokens automatically.
Provides the same interface as SMTPService so the rest of the app
works without changes.
"""
import logging
import re
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = [
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Contacts.Read",
    "https://graph.microsoft.com/User.Read",
    "offline_access",
]

_LABEL_PATTERNS = [
    (re.compile(r"contestar\s+(?:despu[eé]s\s+de\s+)?(\d+)\s+d[ií]a", re.I), "days"),
    (re.compile(r"al\s+final\s+del\s+d[ií]a", re.I), "end_of_day"),
    (re.compile(r"end\s+of\s+(?:the\s+)?day", re.I), "end_of_day"),
    (re.compile(r"\bma[ñn]ana\b|\btomorrow\b", re.I), "tomorrow"),
    (re.compile(r"follow.?up\s+in\s+(\d+)\s+day", re.I), "days"),
    (re.compile(r"reply\s+in\s+(\d+)\s+day", re.I), "days"),
    (re.compile(r"respond\s+in\s+(\d+)\s+day", re.I), "days"),
]


class DelegatedGraphService:
    """
    Microsoft Graph API wrapper using a stored refresh token.
    No SMTP/IMAP needed. Uses the official Microsoft Graph REST API.
    """

    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        self._cached_token = None
        self._token_expiry = None

    # ── Auth ───────────────────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Return a valid access token, refreshing via MSAL if needed."""
        # Use cached token if still valid (5 min buffer)
        if self._cached_token and self._token_expiry and \
                self._token_expiry > datetime.utcnow() + timedelta(minutes=5):
            return self._cached_token

        from app.models import OutlookConnection
        from app.crypto import decrypt, encrypt
        from app import db
        import msal

        conn = OutlookConnection.query.get(self.conn_id)
        if not conn:
            raise RuntimeError("Conexión no encontrada en la base de datos")

        refresh_token = decrypt(conn.password_enc)
        msal_app = msal.PublicClientApplication(
            conn.client_id,
            authority="https://login.microsoftonline.com/common",
        )
        result = msal_app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)

        if "access_token" not in result:
            err = result.get("error_description") or result.get("error", "unknown")
            raise RuntimeError(f"No se pudo renovar el token: {err}")

        # Persist new refresh token if Microsoft rotated it
        if "refresh_token" in result:
            conn.password_enc = encrypt(result["refresh_token"])
            db.session.commit()

        self._cached_token = result["access_token"]
        self._token_expiry = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        return self._cached_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    def _graph(self, method: str, path: str, **kwargs):
        url = f"{GRAPH}/{path.lstrip('/')}"
        resp = getattr(requests, method)(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code == 204:
            return {}
        resp.raise_for_status()
        return resp.json()

    # ── Connection test ────────────────────────────────────────────────────────

    def validate_connection(self):
        try:
            me = self._graph("get", "/me?$select=displayName,mail,userPrincipalName")
            email = me.get("mail") or me.get("userPrincipalName", "")
            name = me.get("displayName", email)
            return True, f"Conexión exitosa como {name} ({email})"
        except Exception as exc:
            return False, str(exc)

    # ── Sending ────────────────────────────────────────────────────────────────

    def send_email(self, to_email: str, subject: str, body_html: str,
                   body_text: str = "", category: str = None,
                   in_reply_to: str = None, references: str = None) -> dict:
        """Send email via Microsoft Graph API."""
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": True,
        }
        if category:
            payload["message"]["categories"] = [category]

        self._graph("post", "/me/sendMail", json=payload)

        # Fetch the sent message to get its ID and conversationId
        result = self._graph(
            "get",
            "/me/mailFolders/SentItems/messages"
            f"?$filter=subject eq '{subject.replace(chr(39), chr(39)*2)}'"
            "&$select=id,conversationId,internetMessageId&$top=1&$orderby=sentDateTime desc",
        )
        msgs = result.get("value", [])
        if msgs:
            m = msgs[0]
            return {
                "message_id": m.get("internetMessageId", ""),
                "conversation_id": m.get("conversationId", ""),
                "graph_id": m.get("id", ""),
            }
        return {"message_id": "", "conversation_id": "", "graph_id": ""}

    # ── Reply detection ────────────────────────────────────────────────────────

    def has_reply(self, conversation_id: str, sent_at: datetime) -> bool:
        """Check if someone else replied to a conversation via Graph."""
        if not conversation_id:
            return False
        try:
            me = self._graph("get", "/me?$select=mail,userPrincipalName")
            my_email = (me.get("mail") or me.get("userPrincipalName", "")).lower()

            since = (sent_at - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = self._graph(
                "get",
                f"/me/messages"
                f"?$filter=conversationId eq '{conversation_id}' and receivedDateTime gt {since}"
                f"&$select=sender,receivedDateTime&$top=20",
            )
            for msg in result.get("value", []):
                sender = msg.get("sender", {}).get("emailAddress", {}).get("address", "").lower()
                if sender and sender != my_email:
                    return True
            return False
        except Exception as exc:
            logger.error("has_reply error: %s", exc)
            return False

    def detect_response_labels(self, conversation_id: str, sent_at: datetime):
        """Scan reply bodies for rescheduling labels."""
        if not conversation_id:
            return None
        try:
            me = self._graph("get", "/me?$select=mail,userPrincipalName")
            my_email = (me.get("mail") or me.get("userPrincipalName", "")).lower()

            since = (sent_at - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            result = self._graph(
                "get",
                f"/me/messages"
                f"?$filter=conversationId eq '{conversation_id}' and receivedDateTime gt {since}"
                f"&$select=sender,body&$top=10",
            )
            for msg in result.get("value", []):
                sender = msg.get("sender", {}).get("emailAddress", {}).get("address", "").lower()
                if sender == my_email:
                    continue
                body_content = msg.get("body", {}).get("content", "")
                body_text = re.sub(r"<[^>]+>", " ", body_content)
                label = _detect_label(body_text)
                if label:
                    return label
            return None
        except Exception as exc:
            logger.error("detect_response_labels error: %s", exc)
            return None

    # ── Contacts ───────────────────────────────────────────────────────────────

    def sync_contacts(self) -> list:
        """Sync contacts from Outlook via Graph API."""
        try:
            result = self._graph(
                "get",
                "/me/contacts?$select=displayName,emailAddresses,jobTitle,companyName&$top=100",
            )
            contacts = []
            for c in result.get("value", []):
                emails = c.get("emailAddresses", [])
                if not emails:
                    continue
                contacts.append({
                    "email": emails[0].get("address", "").lower(),
                    "display_name": c.get("displayName", ""),
                    "job_title": c.get("jobTitle", ""),
                    "company_name": c.get("companyName", ""),
                    "outlook_id": c.get("id", ""),
                })
            return contacts
        except Exception as exc:
            logger.error("sync_contacts error: %s", exc)
            return []

    def ensure_category_exists(self, name: str, color: str = "preset4"):
        """Create an Outlook category if it doesn't already exist."""
        try:
            existing = self._graph("get", "/me/outlook/masterCategories")
            names = [c.get("displayName", "") for c in existing.get("value", [])]
            if name not in names:
                self._graph("post", "/me/outlook/masterCategories",
                            json={"displayName": name, "color": color})
        except Exception as exc:
            logger.warning("ensure_category_exists: %s", exc)


# ── helpers ────────────────────────────────────────────────────────────────────

def _detect_label(text: str):
    for pattern, kind in _LABEL_PATTERNS:
        m = pattern.search(text)
        if m:
            if kind == "days":
                n = int(m.group(1)) if m.lastindex else 1
                return f"{n}_day" if n == 1 else f"{n}_days"
            return kind
    return None
