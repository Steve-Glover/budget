from flask import Flask, render_template
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

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500

    return app
