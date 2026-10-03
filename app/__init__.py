import os

from flask import Flask
from dotenv import load_dotenv

from .database import close_db, init_db


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "purchase_matching.sqlite"),
        PRICE_TOLERANCE_PERCENT=1.0,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    from .routes import bp

    app.register_blueprint(bp)

    with app.app_context():
        init_db()

    return app
