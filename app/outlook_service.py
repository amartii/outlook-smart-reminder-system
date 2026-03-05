"""
outlook_service.py
Microsoft Graph API wrapper for Outlook Smart Reminder System.

Handles authentication (MSAL), email sending, reply detection,
response label parsing, and contact synchronization.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import msal
import requests

logger = logging.getLogger(__name__)

GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/.default"]

# Regex patterns for detecting reminder instructions in reply bodies.
# Each entry: (compiled_pattern, label_type)
_LABEL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"contestar\s+(?:despu[eé]s\s+de\s+)?(\d+)\s+d[ií]a", re.I), "days"),
    (re.compile(r"contestar\s+(?:despu[eé]s\s+de\s+)?(\d+)\s+hora", re.I), "hours"),
    (re.compile(r"al\s+final\s+del\s+d[ií]a", re.I), "end_of_day"),
    (re.compile(r"ma[ñn]ana", re.I), "tomorrow"),
    (re.compile(r"follow.?up\s+in\s+(\d+)\s+day", re.I), "days"),
    (re.compile(r"remind\s+(?:me\s+)?in\s+(\d+)\s+day", re.I), "days"),
    (re.compile(r"remind\s+(?:me\s+)?in\s+(\d+)\s+hour", re.I), "hours"),
    (re.compile(r"recordar\s+en\s+(\d+)\s+d[ií]a", re.I), "days"),
    (re.compile(r"recordar\s+en\s+(\d+)\s+hora", re.I), "hours"),
]

# Map Outlook color preset names to CSS/UI colors for the dashboard
OUTLOOK_COLOR_MAP = {
    "preset0": "#e74856",   # Red
    "preset1": "#ff8c00",   # Orange
    "preset2": "#f4d000",   # Yellow
    "preset3": "#16c60c",   # Green
    "preset4": "#0078d4",   # Blue
    "preset5": "#886ce4",   # Purple
    "preset6": "#00b7c3",   # Teal
    "preset7": "#ff4343",   # DarkRed
    "preset8": "#d13438",   # Cranberry
    "preset9": "#ca5010",   # Pumpkin
    "preset10": "#986f0b",  # Marigold
    "preset11": "#498205",  # ForestGreen
    "preset12": "#038387",  # DarkTeal
    "preset13": "#004e8c",  # DarkBlue
    "preset14": "#881798",  # DarkPurple
    "none": "#6b7280",      # Gray fallback
}


class OutlookService:
    """
    Wrapper for Microsoft Graph API.

    Uses Azure AD client credentials flow (application permissions).
    Requires Mail.Send, Mail.Read, Contacts.Read, User.Read.All.
    """

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_email: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_email = user_email
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    # ── Authentication ────────────────────────────────────────────────────────

    def get_access_token(self) -> str:
        """
        Acquire or refresh an access token using MSAL client credentials.
        Caches the token until 60 seconds before expiry.
        """
        if (
            self._access_token
            and self._token_expires
            and datetime.utcnow() < self._token_expires
        ):
            return self._access_token

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        msal_app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret,
        )
        result = msal_app.acquire_token_for_client(scopes=SCOPES)

        if "access_token" not in result:
            error = result.get("error_description") or result.get("error", "Unknown auth error")
            raise ConnectionError(f"MSAL authentication failed: {error}")

        self._access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)
        logger.info("Access token acquired, valid for %ds", expires_in)
        return self._access_token

    def _headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
        }

    def _get(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Perform authenticated GET request to Graph API."""
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, data: Dict) -> requests.Response:
        """Perform authenticated POST request to Graph API."""
        resp = requests.post(url, headers=self._headers(), json=data, timeout=30)
        resp.raise_for_status()
        return resp

    def _patch(self, url: str, data: Dict) -> requests.Response:
        """Perform authenticated PATCH request to Graph API."""
        resp = requests.patch(url, headers=self._headers(), json=data, timeout=30)
        resp.raise_for_status()
        return resp

    # ── Connection validation ─────────────────────────────────────────────────

    def validate_connection(self) -> Tuple[bool, str]:
        """
        Test that credentials work and the configured mailbox is accessible.
        Returns (success, message).
        """
        try:
            url = f"{GRAPH_ENDPOINT}/users/{self.user_email}"
            data = self._get(url, params={"$select": "displayName,mail,userPrincipalName"})
            display_name = data.get("displayName", self.user_email)
            return True, f"Conectado como {display_name} ({self.user_email})"
        except ConnectionError as exc:
            return False, str(exc)
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status == 401:
                return False, "Error 401: Credenciales inválidas. Verifica Tenant ID, Client ID y Client Secret."
            if status == 403:
                return False, "Error 403: Sin permisos. Asegúrate de que el admin ha dado consentimiento a Mail.Send, Mail.Read, Contacts.Read, User.Read.All."
            if status == 404:
                return False, f"Error 404: Usuario {self.user_email} no encontrado en el tenant."
            return False, f"Error HTTP {status}: {exc.response.text[:300]}"
        except Exception as exc:
            return False, f"Error inesperado: {exc}"

    # ── Email sending ─────────────────────────────────────────────────────────

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        category: Optional[str] = None,
    ) -> Dict:
        """
        Send an email via Microsoft Graph sendMail endpoint.

        Args:
            to_email: Recipient email address.
            subject: Email subject.
            body_html: HTML body content.
            body_text: Plain text fallback (not sent separately, embedded in HTML).
            category: Outlook category name to tag the sent message.

        Returns:
            Dict with 'message_id', 'conversation_id', 'graph_id'.
        """
        message: Dict = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }
        if category:
            message["categories"] = [category]

        url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/sendMail"
        self._post(url, {"message": message, "saveToSentItems": True})
        logger.info("Email sent to %s | subject: %s", to_email, subject)

        # Retrieve the sent message to capture IDs for reply tracking
        return self._fetch_sent_message_ids(to_email, subject)

    def _fetch_sent_message_ids(self, to_email: str, subject: str) -> Dict:
        """
        Fetch the most recently sent message to extract Graph/conversation IDs.
        Falls back gracefully if the message isn't immediately indexed.
        """
        try:
            safe_subject = subject.replace("'", "''")
            url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/mailFolders/SentItems/messages"
            data = self._get(url, params={
                "$filter": (
                    f"subject eq '{safe_subject}' and "
                    f"toRecipients/any(r:r/emailAddress/address eq '{to_email}')"
                ),
                "$orderby": "sentDateTime desc",
                "$top": "1",
                "$select": "id,conversationId,internetMessageId",
            })
            items = data.get("value", [])
            if items:
                return {
                    "message_id": items[0].get("internetMessageId", ""),
                    "conversation_id": items[0].get("conversationId", ""),
                    "graph_id": items[0].get("id", ""),
                }
        except Exception as exc:
            logger.warning("Could not fetch sent message IDs: %s", exc)
        return {"message_id": "", "conversation_id": "", "graph_id": ""}

    # ── Reply detection ───────────────────────────────────────────────────────

    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """
        Fetch all messages belonging to a conversation thread.
        Returns list of message dicts from Graph API.
        """
        url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/messages"
        data = self._get(url, params={
            "$filter": f"conversationId eq '{conversation_id}'",
            "$orderby": "receivedDateTime asc",
            "$select": "id,subject,from,receivedDateTime,body,categories,isDraft",
        })
        return data.get("value", [])

    def has_reply(
        self,
        conversation_id: str,
        original_sent_at: datetime,
    ) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """
        Check whether a conversation has received a reply after the original send time.

        Returns:
            (has_reply, replied_at, reply_body_html)
        """
        try:
            messages = self.get_conversation_messages(conversation_id)
        except Exception as exc:
            logger.error("has_reply error for conversation %s: %s", conversation_id, exc)
            return False, None, None

        for msg in messages:
            if msg.get("isDraft"):
                continue
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
            received_raw = msg.get("receivedDateTime", "")
            if not received_raw:
                continue
            # Graph returns UTC ISO 8601 with Z suffix
            received_at = datetime.fromisoformat(received_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            # A reply is a message not sent by us, received after we sent the original
            if sender != self.user_email.lower() and received_at > original_sent_at:
                body = msg.get("body", {}).get("content", "")
                return True, received_at, body

        return False, None, None

    # ── Response label detection ──────────────────────────────────────────────

    @staticmethod
    def detect_response_labels(message_body: str) -> Optional[str]:
        """
        Parse reply body text for snooze/reminder instruction labels.

        Supported patterns (case-insensitive, Spanish/English):
          - "contestar después de 2 días"  → "2_days"
          - "contestar en 3 horas"         → "3_hours"
          - "al final del día"             → "end_of_day"
          - "mañana"                       → "tomorrow"
          - "follow-up in 5 days"          → "5_days"
          - "remind me in 2 days"          → "2_days"

        Returns normalized label string or None if no pattern matches.
        """
        if not message_body:
            return None

        # Strip HTML tags to analyse plain text
        plain = re.sub(r"<[^>]+>", " ", message_body)
        plain = re.sub(r"\s+", " ", plain).strip()

        for pattern, label_type in _LABEL_PATTERNS:
            match = pattern.search(plain)
            if match:
                if label_type == "days":
                    return f"{match.group(1)}_days"
                if label_type == "hours":
                    return f"{match.group(1)}_hours"
                if label_type == "end_of_day":
                    return "end_of_day"
                if label_type == "tomorrow":
                    return "tomorrow"

        return None

    # ── Contacts ──────────────────────────────────────────────────────────────

    def sync_contacts(self) -> List[Dict]:
        """
        Fetch all contacts from the user's Outlook contacts folder via Graph API.

        Returns list of dicts with keys:
            outlook_id, display_name, email, job_title, company_name
        """
        contacts: List[Dict] = []
        url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/contacts"
        params: Optional[Dict] = {
            "$select": "id,displayName,emailAddresses,jobTitle,companyName",
            "$top": "100",
        }

        while url:
            data = self._get(url, params=params)
            for item in data.get("value", []):
                email_addresses = item.get("emailAddresses", [])
                if not email_addresses:
                    continue
                primary_email = email_addresses[0].get("address", "").strip().lower()
                if not primary_email:
                    continue
                contacts.append({
                    "outlook_id": item.get("id", ""),
                    "display_name": item.get("displayName", ""),
                    "email": primary_email,
                    "job_title": item.get("jobTitle", ""),
                    "company_name": item.get("companyName", ""),
                })
            # Follow pagination
            url = data.get("@odata.nextLink")
            params = None  # nextLink already contains all params

        logger.info("sync_contacts: fetched %d contacts from Outlook", len(contacts))
        return contacts

    # ── Outlook categories ────────────────────────────────────────────────────

    def get_master_categories(self) -> List[Dict]:
        """Get all Outlook master categories defined for the user."""
        url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/outlook/masterCategories"
        data = self._get(url)
        return data.get("value", [])

    def create_master_category(self, name: str, color: str = "preset0") -> Dict:
        """
        Create a new Outlook master category.

        Args:
            name: Display name (e.g. "Manager").
            color: Outlook color preset (preset0–preset24).
        """
        url = f"{GRAPH_ENDPOINT}/users/{self.user_email}/outlook/masterCategories"
        resp = self._post(url, {"displayName": name, "color": color})
        return resp.json()

    def ensure_category_exists(self, name: str, color: str = "preset0") -> bool:
        """
        Create the Outlook master category only if it doesn't already exist.
        Returns True if created or already existed.
        """
        try:
            existing = [c["displayName"] for c in self.get_master_categories()]
            if name not in existing:
                self.create_master_category(name, color)
                logger.info("Created Outlook master category: %s (%s)", name, color)
            return True
        except Exception as exc:
            logger.warning("Could not ensure category '%s': %s", name, exc)
            return False
