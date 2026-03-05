"""
scheduler.py
APScheduler background jobs for Outlook Smart Reminder System.

Jobs:
  - sync_contacts_job    : sync Outlook contacts every 6h
  - check_responses_job  : check for email replies every 15min
  - send_reminders_job   : fire pending reminders every 1h
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def _build_outlook_service(app):
    """
    Build an OutlookService instance from the active OutlookConnection in the DB.
    Returns None if no active connection is configured.
    """
    from app.models import OutlookConnection
    from app.outlook_service import OutlookService
    from app.crypto import decrypt

    conn = OutlookConnection.query.filter_by(is_active=True).first()
    if not conn:
        logger.debug("No active Outlook connection — skipping job")
        return None

    client_secret = decrypt(conn.client_secret_enc)
    return OutlookService(conn.tenant_id, conn.client_id, client_secret, conn.user_email)


def sync_contacts_job(app):
    """
    Sync contacts from Outlook into the local DB.
    Creates new Contact records; updates existing ones by email (upsert).
    """
    with app.app_context():
        from app import db
        from app.models import Contact

        svc = _build_outlook_service(app)
        if not svc:
            return

        try:
            contacts_data = svc.sync_contacts()
        except Exception as exc:
            logger.error("sync_contacts_job error: %s", exc)
            return

        new_count = 0
        for c in contacts_data:
            if not c.get("email"):
                continue
            existing = Contact.query.filter_by(email=c["email"]).first()
            if existing:
                existing.display_name = c["display_name"] or existing.display_name
                existing.job_title = c["job_title"] or existing.job_title
                existing.company_name = c["company_name"] or existing.company_name
                existing.outlook_id = c["outlook_id"] or existing.outlook_id
                existing.updated_at = datetime.utcnow()
            else:
                db.session.add(Contact(
                    email=c["email"],
                    display_name=c["display_name"],
                    job_title=c["job_title"],
                    company_name=c["company_name"],
                    outlook_id=c["outlook_id"],
                ))
                new_count += 1

        db.session.commit()
        logger.info("sync_contacts_job: %d new contacts imported (%d total)", new_count, len(contacts_data))


def check_responses_job(app):
    """
    Check all pending SentEmails for replies via Graph API conversation tracking.
    If a reply is detected, updates status and parses response labels to reschedule.
    """
    with app.app_context():
        from app import db
        from app.models import SentEmail
        from app.outlook_service import OutlookService
        from app.category_manager import CategoryManager

        svc = _build_outlook_service(app)
        if not svc:
            return

        pending = SentEmail.query.filter(
            SentEmail.status.in_(["pending", "snoozed"]),
            SentEmail.conversation_id.isnot(None),
            SentEmail.replied_at.is_(None),
        ).all()

        if not pending:
            return

        replied_count = 0
        for se in pending:
            try:
                has_reply, replied_at, body = svc.has_reply(se.conversation_id, se.sent_at)
                if not has_reply:
                    continue

                se.replied_at = replied_at or datetime.utcnow()
                se.status = "replied"
                replied_count += 1
                logger.info("Reply detected for SentEmail %d", se.id)

                # Check if reply contains a snooze/reschedule label
                label = OutlookService.detect_response_labels(body or "")
                if label:
                    logger.info("Label '%s' found in reply for SentEmail %d", label, se.id)
                    CategoryManager.process_response_label(se.id, label)

            except Exception as exc:
                logger.error("check_responses_job error for SentEmail %d: %s", se.id, exc)

        db.session.commit()
        logger.info("check_responses_job complete — %d replies detected", replied_count)


def send_reminders_job(app):
    """
    Find and send all reminders that are due right now.
    """
    with app.app_context():
        from app.reminder_engine import ReminderEngine

        svc = _build_outlook_service(app)
        if not svc:
            return

        due = ReminderEngine.get_pending_reminders()
        if not due:
            return

        sent_count = 0
        for se in due:
            if ReminderEngine.send_reminder(se.id, svc):
                sent_count += 1

        logger.info("send_reminders_job complete — %d reminders sent", sent_count)


def start_scheduler(app):
    """
    Register all jobs and start the APScheduler background scheduler.
    Intervals are read from app config so they can be overridden via env vars.
    """
    sync_hours = app.config.get("SYNC_CONTACTS_INTERVAL_HOURS", 6)
    check_minutes = app.config.get("CHECK_RESPONSES_INTERVAL_MINUTES", 15)
    reminder_hours = app.config.get("SEND_REMINDERS_INTERVAL_HOURS", 1)

    scheduler.add_job(
        func=sync_contacts_job,
        args=[app],
        trigger="interval",
        hours=sync_hours,
        id="sync_contacts",
        replace_existing=True,
    )
    scheduler.add_job(
        func=check_responses_job,
        args=[app],
        trigger="interval",
        minutes=check_minutes,
        id="check_responses",
        replace_existing=True,
    )
    scheduler.add_job(
        func=send_reminders_job,
        args=[app],
        trigger="interval",
        hours=reminder_hours,
        id="send_reminders",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info(
            "Scheduler started — sync_contacts(%dh), check_responses(%dmin), send_reminders(%dh)",
            sync_hours, check_minutes, reminder_hours,
        )

