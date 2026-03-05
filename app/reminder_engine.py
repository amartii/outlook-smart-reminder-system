"""
reminder_engine.py
Core logic for detecting pending reminders and dispatching them via Outlook.
"""
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


class ReminderEngine:
    """
    Checks the database for SentEmails that are overdue for a reminder
    and sends those reminders via the Outlook Graph API.
    """

    @staticmethod
    def get_pending_reminders() -> List:
        """
        Return all SentEmail records that are due for a reminder right now.

        A SentEmail is due when:
          - status is 'pending' or 'snoozed'
          - reminder has not been sent yet (reminder_sent_at IS NULL)
          - effective_reminder_at (custom or default) is in the past
        """
        from app.models import SentEmail
        now = datetime.utcnow()
        candidates = SentEmail.query.filter(
            SentEmail.status.in_(["pending", "snoozed"]),
            SentEmail.reminder_sent_at.is_(None),
        ).all()
        return [se for se in candidates if se.effective_reminder_at and se.effective_reminder_at <= now]

    @staticmethod
    def get_upcoming_reminders(hours_ahead: int = 24) -> List:
        """
        Return SentEmails with a reminder scheduled within the next N hours.
        Used by the dashboard to show upcoming actions.
        """
        from app.models import SentEmail
        from datetime import timedelta
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        candidates = SentEmail.query.filter(
            SentEmail.status.in_(["pending", "snoozed"]),
            SentEmail.reminder_sent_at.is_(None),
        ).all()
        return [
            se for se in candidates
            if se.effective_reminder_at and now < se.effective_reminder_at <= cutoff
        ]

    @staticmethod
    def send_reminder(sent_email_id: int, outlook_service) -> bool:
        """
        Send a reminder email for the given SentEmail record.

        Builds a personalised reminder body referencing the original email
        and the hours elapsed since it was sent.

        Args:
            sent_email_id: Primary key of the SentEmail to remind about.
            outlook_service: An initialised OutlookService instance.

        Returns:
            True on success, False on failure.
        """
        from app import db
        from app.models import SentEmail, Reminder
        sent_email = SentEmail.query.get(sent_email_id)
        if not sent_email:
            logger.error("send_reminder: SentEmail %d not found", sent_email_id)
            return False

        contact = sent_email.contact
        if not contact:
            logger.error("send_reminder: no contact for SentEmail %d", sent_email_id)
            return False

        name = contact.display_name or contact.email
        hours_elapsed = 0
        if sent_email.sent_at:
            delta = datetime.utcnow() - sent_email.sent_at
            hours_elapsed = int(delta.total_seconds() / 3600)

        subject = f"Re: {sent_email.subject}"
        body_html = f"""
<p>Hola {name},</p>
<p>Te escribimos hace <strong>{hours_elapsed} horas</strong> sobre: <em>{sent_email.subject}</em></p>
<p>Queremos asegurarnos de que recibiste nuestro mensaje y ver si tienes alguna pregunta.</p>
<p>Quedo a tu disposición.</p>
<hr>
<p style="color:#666;font-size:0.85em;">
  <em>Este es un recordatorio automático del sistema Outlook Smart Reminder.</em><br>
  Si ya no deseas recibir recordatorios para este hilo, responde con "cerrar" o "close".
</p>
"""
        category_name = contact.category_rule.name if contact.category_rule else None

        try:
            result = outlook_service.send_email(
                to_email=contact.email,
                subject=subject,
                body_html=body_html,
                category=category_name,
            )
            now = datetime.utcnow()
            sent_email.reminder_sent_at = now
            sent_email.status = "reminder_sent"

            reminder_log = Reminder(
                sent_email_id=sent_email_id,
                sent_at=now,
                notes=(
                    f"Reminder sent after {hours_elapsed}h. "
                    f"Graph ID: {result.get('graph_id', 'n/a')}"
                ),
            )
            db.session.add(reminder_log)
            db.session.commit()
            logger.info(
                "Reminder sent: SentEmail %d → %s (after %dh)",
                sent_email_id, contact.email, hours_elapsed,
            )
            return True

        except Exception as exc:
            logger.error("send_reminder failed for SentEmail %d: %s", sent_email_id, exc)
            return False

    @staticmethod
    def snooze(sent_email_id: int, hours: int) -> bool:
        """
        Manually snooze a reminder by N hours from now.
        Resets reminder_sent_at so the engine can re-fire later.
        """
        from app import db
        from app.models import SentEmail
        from datetime import timedelta
        sent_email = SentEmail.query.get(sent_email_id)
        if not sent_email:
            return False
        sent_email.custom_reminder_at = datetime.utcnow() + timedelta(hours=hours)
        sent_email.reminder_sent_at = None
        sent_email.status = "snoozed"
        db.session.commit()
        logger.info("SentEmail %d snoozed for %dh", sent_email_id, hours)
        return True

    @staticmethod
    def close(sent_email_id: int) -> bool:
        """Mark a SentEmail as closed — no further reminders will be sent."""
        from app import db
        from app.models import SentEmail
        sent_email = SentEmail.query.get(sent_email_id)
        if not sent_email:
            return False
        sent_email.status = "closed"
        db.session.commit()
        logger.info("SentEmail %d closed", sent_email_id)
        return True
