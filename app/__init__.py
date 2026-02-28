from flask import Flask
from config import config
from app.extensions import db, migrate, csrf, login_manager


def create_app(config_name=None):
    if config_name is None:
        import os

        config_name = os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    # Import models so Alembic can detect them
    from app import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User

        return db.session.get(User, int(user_id))

    from app.routes import register_blueprints

    register_blueprints(app)

    return app
