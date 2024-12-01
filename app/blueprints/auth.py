from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import (
    confirm_login,
    current_user,
    login_fresh,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import select

from app.config import Operations
from app.emails import send_confirmation_email, send_reset_password_email
from app.extensions import db
from app.forms.auth import (
    ForgetPasswordForm,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
)
from app.models import User
from app.utils import redirect_back

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data.lower()
        username = form.username.data
        password = form.password.data
        user = User(name=name, email=email, username=username, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        token = user.generate_token(operation=Operations.CONFIRM)
        send_confirmation_email(user=user, token=token)
        flash("Confirmation email sent, please check your inbox.", "info")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@auth.get("/confirm/<token>")
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    if current_user.parse_token(token=token, operation=Operations.CONFIRM):
        current_user.confirmed = True
        db.session.commit()
        flash("Account confirmed.", "success")
        return redirect(url_for("main.index"))
    flash("Invalid or expired token.", "danger")
    return redirect(url_for(".resend_confirmation_email"))


@auth.get("/resend-confirmation-email")
@login_required
def resend_confirmation_email():
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    token = current_user.generate_token(operation=Operations.CONFIRM)
    send_confirmation_email(user=current_user, token=token)
    flash("New email sent, please check your inbox.", "info")
    return redirect(url_for("main.index"))


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).filter_by(email=form.email.data.lower()))
        if user is not None and user.check_password(form.password.data):
            if login_user(user, form.remember_me.data):
                flash("Login success.", "info")
                return redirect_back()
            else:
                flash("Your account is blocked.", "warning")
                return redirect(url_for("main.index"))
        flash("Invalid email or password.", "warning")
        return redirect(url_for(".login"))
    return render_template("auth/login.html", form=form)


@auth.route("/forget-password", methods=["GET", "POST"])
def forget_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ForgetPasswordForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).filter_by(email=form.email.data.lower()))
        if user is None:
            flash("Invalid email.", "warning")
            return redirect(url_for(".forget_password"))
        token = user.generate_token(operation=Operations.RESET_PASSWORD)
        send_reset_password_email(user=user, token=token)
        flash("Password reset email sent, please check your inbox.", "info")
        return redirect(url_for(".login"))
    return render_template("auth/reset_password.html", form=form)


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).filter_by(email=form.email.data.lower()))
        if user is None:
            return redirect(url_for("main.index"))
        if not user.parse_token(token=token, operation=Operations.RESET_PASSWORD):
            flash("Invalid or expired token.", "danger")
            return redirect(url_for(".forget_password"))
        user.password = form.password.data
        db.session.commit()
        flash("Password updated.", "success")
        return redirect(url_for(".login"))
    return render_template("auth/reset_password.html", form=form)


@auth.route("/re-authenticate", methods=["GET", "POST"])
@login_required
def re_authenticated():
    if login_fresh():
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit() and current_user.check_password(form.password.data):
        confirm_login()
        return redirect_back()
    return render_template("auth/login.html", form=form)


@auth.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout success.", "info")
    return redirect(url_for("main.index"))
