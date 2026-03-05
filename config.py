import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "agent.db") + "?check_same_thread=False"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_API_ENABLED = True

    # Microsoft Graph / Azure AD
    OUTLOOK_TENANT_ID = os.environ.get("OUTLOOK_TENANT_ID", "")
    OUTLOOK_CLIENT_ID = os.environ.get("OUTLOOK_CLIENT_ID", "")
    OUTLOOK_CLIENT_SECRET = os.environ.get("OUTLOOK_CLIENT_SECRET", "")
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    # Scheduler intervals (seconds)
    SYNC_CONTACTS_INTERVAL_HOURS = int(os.environ.get("SYNC_CONTACTS_INTERVAL_HOURS", 6))
    CHECK_RESPONSES_INTERVAL_MINUTES = int(os.environ.get("CHECK_RESPONSES_INTERVAL_MINUTES", 15))
    SEND_REMINDERS_INTERVAL_HOURS = int(os.environ.get("SEND_REMINDERS_INTERVAL_HOURS", 1))
