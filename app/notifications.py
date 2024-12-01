from flask import url_for

from app.extensions import db
from app.models import Notification


def push_follow_notification(follower, receiver):
    user_url = url_for("user.index", username=follower.username)
    message = f'User <a href="{user_url}">{follower.username}</a> followed you.'
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_comment_notification(photo_id, receiver, page=1):
    photo_url = url_for("main.show_photo", id=photo_id, page=page)
    message = (
        f'User <a href="{photo_url}#comments">This photo</a> has new comment/reply.'
    )
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_collect_notification(user, photo_id, receiver):
    user_url = url_for("user.index", username=user.username)
    photo_url = url_for("main.show_photo", id=photo_id)
    message = f'User <a href="{user_url}">{user.username}</a> collected your <a href="{photo_url}">photo</a>.'
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()
