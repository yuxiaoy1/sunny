from flask import Flask

from app.blueprints.admin import admin
from app.blueprints.ajax import ajax
from app.blueprints.auth import auth
from app.blueprints.commands import commands
from app.blueprints.errors import errors
from app.blueprints.main import main
from app.blueprints.templating import templating
from app.blueprints.user import user
from app.config import config
from app.extensions import (
    avatars,
    bootstrap,
    csrf,
    db,
    dropzone,
    login,
    mail,
    whooshee,
)


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # extensions
    bootstrap.init_app(app)
    db.init_app(app)
    login.init_app(app)
    mail.init_app(app)
    avatars.init_app(app)
    dropzone.init_app(app)
    csrf.init_app(app)
    whooshee.init_app(app)

    # blueprints
    app.register_blueprint(commands)
    app.register_blueprint(errors)
    app.register_blueprint(templating)
    app.register_blueprint(main)
    app.register_blueprint(user, url_prefix="/user")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(ajax, url_prefix="/ajax")

    return app
