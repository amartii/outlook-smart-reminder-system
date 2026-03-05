from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os

db = SQLAlchemy()


def create_app(config_class=Config):
    app = Flask(__name__, static_folder="../static", template_folder="templates")
    app.config.from_object(config_class)

    os.makedirs(os.path.join(os.path.dirname(app.instance_path), "instance"), exist_ok=True)

    db.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app
