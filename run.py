import logging
from app import create_app
from app.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = create_app()

if __name__ == "__main__":
    start_scheduler(app)
    print("🚀 Outlook Smart Reminder en http://localhost:5000  (Ctrl+C para parar)")
    app.run(debug=False, port=5000, use_reloader=False)
