from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user
from markupsafe import Markup

from app.models import Permission


def confirm_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if not current_user.confirmed:
            message = Markup(
                'Please confirm your account first. Didn\'t receive the email? '
                f'<a class="alert-link" href="{url_for('auth.resend_confirmation_email')}">Resend Confirmation Email</a>'
            )
            flash(message, "warning")
            return redirect(url_for("main.index"))
        return func(*args, **kwargs)

    return inner


def permission_required(perm):
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if not current_user.can(perm):
                abort(403)
            return func(*args, **kwargs)

        return inner

    return decorator


def admin_required(func):
    return permission_required(Permission.ADMIN)(func)
