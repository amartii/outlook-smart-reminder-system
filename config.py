import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "agent.db") + "?check_same_thread=False"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_API_ENABLED = True

    # Scheduler intervals
    SYNC_CONTACTS_INTERVAL_HOURS = int(os.environ.get("SYNC_CONTACTS_INTERVAL_HOURS", 6))
    CHECK_RESPONSES_INTERVAL_MINUTES = int(os.environ.get("CHECK_RESPONSES_INTERVAL_MINUTES", 15))
    SEND_REMINDERS_INTERVAL_HOURS = int(os.environ.get("SEND_REMINDERS_INTERVAL_HOURS", 1))
