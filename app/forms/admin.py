from sqlalchemy import select
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

from app.extensions import db
from app.forms.user import EditProfileForm
from app.models import Role, User


class EditProfileAdminForm(EditProfileForm):
    email = StringField("Email", validators=[DataRequired(), Length(1, 254), Email()])
    role = SelectField("Role", coerce=int)
    active = BooleanField("Active")
    confirmed = BooleanField("Confirmed")
    submit = SubmitField()

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        roles = db.session.scalars(select(Role).order_by(Role.name)).all()
        self.role.choices = [(r.id, r.name) for r in roles]
        self.user = user

    def validate_username(self, field):
        user = db.session.scalar(select(User).filter_by(username=field.data))
        if field.data != self.user.username and user:
            raise ValidationError("The username is already in use.")

    def validate_email(self, field):
        email = db.session.scalar(select(User).filter_by(email=field.data.lower()))
        if field.data != self.user.email and email:
            raise ValidationError("The email is already in use.")
