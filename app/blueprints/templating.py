from flask import Blueprint
from flask_login import current_user
from sqlalchemy import func, select

from app.extensions import db
from app.models import Notification, Permission

templating = Blueprint("templating", __name__)


@templating.app_context_processor
def make_template_context():
    notification_count = None
    if current_user.is_authenticated:
        notification_count = db.session.scalar(
            select(func.count(Notification.id)).filter_by(
                receiver_id=current_user.id, is_read=False
            )
        )
    return dict(notification_count=notification_count, Permission=Permission)
