from threading import Thread

from flask import current_app, render_template
from flask_mailman import EmailMessage


def _send_async_email(app, message):
    with app.app_context():
        message.send()


def send_email(subject, body, to):
    app = current_app._get_current_object()
    messsage = EmailMessage(subject, body=body, to=[to])
    messsage.content_subtype = "html"
    thr = Thread(target=_send_async_email, args=[app, messsage])
    thr.start()
    return thr


def send_confirmation_email(user, token, to=None):
    send_email(
        "Email Confirmation",
        render_template("emails/confirmation.html", user=user, token=token),
        to=to or user.email,
    )


def send_reset_password_email(user, token, to=None):
    send_email(
        "Password Reset",
        render_template("emails/reset_password.html", user=user, token=token),
        to=to or user.email,
    )


def send_change_email_email(user, token, to=None):
    send_email(
        "Change Email Confirmation",
        render_template("emails/change_email.html", user=user, token=token),
        to=to or user.email,
    )
