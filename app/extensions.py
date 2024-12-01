from flask_avatars import Avatars
from flask_bootstrap import Bootstrap5
from flask_dropzone import Dropzone
from flask_login import AnonymousUserMixin, LoginManager
from flask_mailman import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_whooshee import Whooshee
from flask_wtf import CSRFProtect

db = SQLAlchemy()
bootstrap = Bootstrap5()
login = LoginManager()
mail = Mail()
avatars = Avatars()
dropzone = Dropzone()
csrf = CSRFProtect()
whooshee = Whooshee()


@login.user_loader
def load_user(id):
    from app.models import User

    return db.session.get(User, id)


class AnonymousUser(AnonymousUserMixin):
    @property
    def is_admin(self):
        return False

    def can(self, perm):
        return False


login.anonymous_user = AnonymousUser
login.login_view = "auth.login"
login.login_message_category = "warning"
login.refresh_view = "auth.re_authenticated"
login.needs_refresh_message_category = "warning"
