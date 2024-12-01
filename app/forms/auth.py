from flask_wtf import FlaskForm
from sqlalchemy import select
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
    ValidationError,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp

from app.extensions import db
from app.models import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 254), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Log in")


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(1, 30)])
    email = StringField("Email", validators=[DataRequired(), Length(1, 254), Email()])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(1, 20),
            Regexp(
                "^[a-zA-Z0-9]*$",
                message="The username should contain only a-z, A-Z and 0-9.",
            ),
        ],
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(8, 128), EqualTo("password2")]
    )
    password2 = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
        ],
    )
    submit = SubmitField()

    def validate_email(self, field):
        user = db.session.scalar(select(User).filter_by(email=field.data.lower()))
        if user:
            raise ValidationError("The email is already in user.")

    def validate_username(self, field):
        user = db.session.scalar(select(User).filter_by(username=field.data.lower()))
        if user:
            raise ValidationError("The username is already in user.")


class ForgetPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 254), Email()])
    submit = SubmitField()


class ResetPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 254), Email()])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(8, 128), EqualTo("password2")]
    )
    password2 = PasswordField("Confirm password", validators=[DataRequired()])
    submit = SubmitField()
