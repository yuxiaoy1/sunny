from flask import Blueprint, abort, render_template
from flask_login import current_user
from sqlalchemy import func, select

from app.extensions import db
from app.models import Permission, Photo, User
from app.notifications import push_collect_notification

ajax = Blueprint("ajax", __name__)


@ajax.get("/profile/<int:id>")
def get_profile(id):
    user = db.get_or_404(User, id)
    return render_template("main/profile_popup.html", user=user)


@ajax.post("/follow/<username>")
def follow(username):
    if not current_user.is_authenticated:
        return {"message": "Login required."}, 403
    if not current_user.confirmed:
        return {"message": "Confirm account required."}, 400
    if not current_user.can(Permission.FOLLOW):
        return {"message": "No permission."}, 403
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    if current_user.is_following(user):
        return {"message": "Already followed."}, 400
    current_user.follow(user)
    return {"message": "User followed."}


@ajax.post("/unfollow/<username>")
def unfollow(username):
    if not current_user.is_authenticated:
        return {"message": "Login required."}, 403
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    if not current_user.is_following(user):
        return {"message": "Not following yet."}, 400
    current_user.unfollow(user)
    return {"message": "Follow canceled."}


@ajax.post("/collect/<int:id>")
def collect(id):
    if not current_user.is_authenticated:
        return {"message": "Login required."}, 403
    if not current_user.confirmed:
        return {"message": "Confirm account required."}, 400
    if not current_user.can(Permission.COLLECT):
        return {"message": "No permission."}, 403
    photo = db.get_or_404(Photo, id)
    if current_user.is_collecting(photo):
        return {"message": "Already collected."}, 400
    current_user.collect(photo)
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(user=current_user, photo_id=id, receiver=photo.author)
    return {"message": "Photo collected."}


@ajax.post("/uncollect/<int:id>")
def uncollect(id):
    if not current_user.is_authenticated:
        return {"message": "Login required."}, 403
    photo = db.get_or_404(Photo, id)
    if not current_user.is_collecting(photo):
        return {"message": "Not collect yet."}, 400
    current_user.uncollect(photo)
    return {"message": "Collect canceled."}


@ajax.get("/followers-count/<int:id>")
def followers_count(id):
    user = db.get_or_404(User, id)
    return {"count": user.followers_count}


@ajax.get("/collectors-count/<int:id>")
def collectors_count(id):
    photo = db.get_or_404(Photo, id)
    return {"count": photo.collectors_count}


@ajax.get("/notifications-count")
def notifications_count():
    if not current_user.is_authenticated:
        return {"message": "Login required."}, 403
    count = db.session.scalar(
        current_user.notifications.select()
        .filter_by(is_read=False)
        .with_only_columns(func.count())
    )
    return {"count": count}
