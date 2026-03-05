"""
models.py
SQLAlchemy models for Outlook Smart Reminder System.
"""
from datetime import datetime
from app import db


class OutlookConnection(db.Model):
    """Stores email credentials (SMTP/IMAP) for the sending mailbox."""

    __tablename__ = "outlook_connections"

    id = db.Column(db.Integer, primary_key=True)
    # backend_type: 'smtp' (default) or 'graph' (legacy Azure AD)
    backend_type = db.Column(db.String(20), default="smtp", nullable=False)
    user_email = db.Column(db.String(200), nullable=False)   # sender address
    display_name = db.Column(db.String(200))
    password_enc = db.Column(db.Text, nullable=False)        # encrypted with Fernet
    smtp_host = db.Column(db.String(200), default="smtp.office365.com")
    smtp_port = db.Column(db.Integer, default=587)
    imap_host = db.Column(db.String(200), default="outlook.office365.com")
    imap_port = db.Column(db.Integer, default=993)
    # Legacy Azure AD fields (kept for compatibility, nullable)
    tenant_id = db.Column(db.String(200))
    client_id = db.Column(db.String(200))
    client_secret_enc = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sent_emails = db.relationship("SentEmail", backref="connection", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "backend_type": self.backend_type,
            "user_email": self.user_email,
            "display_name": self.display_name,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "imap_host": self.imap_host,
            "imap_port": self.imap_port,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CategoryRule(db.Model):
    """Defines reminder timing rules per Outlook category."""

    __tablename__ = "category_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    # Outlook color preset names: preset0–preset24
    color = db.Column(db.String(50), default="preset0")
    # Hours to wait before sending a reminder (e.g. 72 = 3 days)
    reminder_hours = db.Column(db.Integer, default=72)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contacts = db.relationship("Contact", backref="category_rule", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "reminder_hours": self.reminder_hours,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Contact(db.Model):
    """Contact synchronized from Outlook or added manually."""

    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    display_name = db.Column(db.String(200))
    job_title = db.Column(db.String(200))
    company_name = db.Column(db.String(200))
    outlook_id = db.Column(db.String(500))   # Graph contact resource ID
    category_id = db.Column(db.Integer, db.ForeignKey("category_rules.id"), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sent_emails = db.relationship("SentEmail", backref="contact", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "outlook_id": self.outlook_id,
            "category_id": self.category_id,
            "category_name": self.category_rule.name if self.category_rule else None,
            "category_color": self.category_rule.color if self.category_rule else None,
            "reminder_hours": self.category_rule.reminder_hours if self.category_rule else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SentEmail(db.Model):
    """Tracks sent emails and their reminder schedule."""

    __tablename__ = "sent_emails"

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id"), nullable=False)
    connection_id = db.Column(db.Integer, db.ForeignKey("outlook_connections.id"), nullable=False)
    subject = db.Column(db.Text, nullable=False)
    body_preview = db.Column(db.Text)        # first ~300 chars for dashboard display
    message_id = db.Column(db.String(500))   # SMTP/Graph internet message ID
    conversation_id = db.Column(db.String(500))  # Graph conversation ID for reply tracking
    graph_message_id = db.Column(db.String(500)) # Graph internal message ID
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    replied_at = db.Column(db.DateTime)
    # Calculated from category rule at send time
    reminder_at = db.Column(db.DateTime)
    reminder_sent_at = db.Column(db.DateTime)
    # Overrides reminder_at when a response label reschedules it
    custom_reminder_at = db.Column(db.DateTime)
    # Normalized label detected in reply: "2_days", "end_of_day", "tomorrow", etc.
    response_label = db.Column(db.String(100))
    # pending | replied | reminder_sent | snoozed | closed
    status = db.Column(db.String(20), default="pending")

    reminders = db.relationship("Reminder", backref="sent_email", lazy=True)

    @property
    def effective_reminder_at(self):
        """Return custom reminder if set, otherwise the category-based one."""
        return self.custom_reminder_at or self.reminder_at

    def to_dict(self):
        contact = self.contact
        return {
            "id": self.id,
            "contact": contact.to_dict() if contact else None,
            "subject": self.subject,
            "body_preview": self.body_preview,
            "conversation_id": self.conversation_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "reminder_at": self.effective_reminder_at.isoformat() if self.effective_reminder_at else None,
            "reminder_sent_at": self.reminder_sent_at.isoformat() if self.reminder_sent_at else None,
            "response_label": self.response_label,
            "status": self.status,
            "reminders_count": len(self.reminders),
        }


class Reminder(db.Model):
    """Log entry for each reminder sent."""

    __tablename__ = "reminders"

    id = db.Column(db.Integer, primary_key=True)
    sent_email_id = db.Column(db.Integer, db.ForeignKey("sent_emails.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "sent_email_id": self.sent_email_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "notes": self.notes,
        }

