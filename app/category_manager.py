"""
category_manager.py
Logic for assigning Outlook categories to contacts and computing reminder schedules.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_REMINDER_HOURS = 72  # 3 days fallback when no category is assigned


class CategoryManager:
    """
    Manages the relationship between contacts, category rules, and reminder timing.

    Category rules define how many hours to wait before sending a reminder
    to a contact who hasn't replied (e.g. Blue = 24h, Manager = 48h, Senior = 72h).
    """

    @staticmethod
    def get_reminder_hours(contact_id: int) -> int:
        """
        Return the reminder hours for a contact based on their assigned category rule.
        Falls back to DEFAULT_REMINDER_HOURS if no category is assigned.
        """
        from app.models import Contact
        contact = Contact.query.get(contact_id)
        if contact and contact.category_rule:
            return contact.category_rule.reminder_hours
        return DEFAULT_REMINDER_HOURS

    @staticmethod
    def calculate_reminder_at(sent_at: datetime, reminder_hours: int) -> datetime:
        """Calculate the absolute datetime when the reminder should fire."""
        return sent_at + timedelta(hours=reminder_hours)

    @staticmethod
    def assign_category(contact_id: int, category_id: int) -> bool:
        """
        Assign a CategoryRule to a Contact.
        Returns True on success, False if contact or rule not found.
        """
        from app import db
        from app.models import Contact, CategoryRule
        contact = Contact.query.get(contact_id)
        rule = CategoryRule.query.get(category_id)
        if not contact or not rule:
            return False
        contact.category_id = category_id
        db.session.commit()
        logger.info("Assigned category '%s' to contact %s", rule.name, contact.email)
        return True

    @staticmethod
    def process_response_label(sent_email_id: int, label: str) -> Optional[datetime]:
        """
        Reschedule a reminder based on a label detected in a reply body.

        Supported labels:
            "N_days"     → now + N days
            "N_hours"    → now + N hours
            "end_of_day" → today at 17:00 (or tomorrow 17:00 if past that time)
            "tomorrow"   → tomorrow at 09:00

        Updates SentEmail.custom_reminder_at and sets status to 'snoozed'.
        Returns the new reminder datetime or None if label is unrecognised.
        """
        from app import db
        from app.models import SentEmail
        sent_email = SentEmail.query.get(sent_email_id)
        if not sent_email:
            logger.warning("process_response_label: SentEmail %d not found", sent_email_id)
            return None

        now = datetime.utcnow()
        new_reminder: Optional[datetime] = None

        if label.endswith("_days"):
            try:
                n = int(label.split("_")[0])
                new_reminder = now + timedelta(days=n)
            except (ValueError, IndexError):
                logger.warning("Cannot parse days label: %s", label)

        elif label.endswith("_hours"):
            try:
                n = int(label.split("_")[0])
                new_reminder = now + timedelta(hours=n)
            except (ValueError, IndexError):
                logger.warning("Cannot parse hours label: %s", label)

        elif label == "end_of_day":
            new_reminder = now.replace(hour=17, minute=0, second=0, microsecond=0)
            if new_reminder <= now:
                new_reminder += timedelta(days=1)

        elif label == "tomorrow":
            new_reminder = (now + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        if new_reminder:
            sent_email.custom_reminder_at = new_reminder
            sent_email.response_label = label
            sent_email.status = "snoozed"
            db.session.commit()
            logger.info(
                "Reminder rescheduled: SentEmail %d label=%s new_reminder=%s",
                sent_email_id, label, new_reminder,
            )

        return new_reminder

    @staticmethod
    def seed_default_categories() -> None:
        """
        Insert the default category rules into the DB if they don't exist yet.
        Called on app startup so users have a sensible starting point.
        """
        from app import db
        from app.models import CategoryRule
        defaults = [
            {"name": "Blue",           "color": "preset4",  "reminder_hours": 24,  "description": "Respuesta en 24 horas"},
            {"name": "Manager",        "color": "preset3",  "reminder_hours": 48,  "description": "Respuesta en 48 horas"},
            {"name": "Senior Manager", "color": "preset1",  "reminder_hours": 72,  "description": "Respuesta en 72 horas (3 días)"},
            {"name": "VIP",            "color": "preset0",  "reminder_hours": 96,  "description": "Respuesta en 4 días"},
        ]
        for d in defaults:
            if not CategoryRule.query.filter_by(name=d["name"]).first():
                db.session.add(CategoryRule(**d))
        db.session.commit()
        logger.info("Default categories seeded")
