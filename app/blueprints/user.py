from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, fresh_login_required, login_required, logout_user
from sqlalchemy import select

from app.config import Operations
from app.decorators import confirm_required, permission_required
from app.emails import send_change_email_email
from app.extensions import avatars, db
from app.forms.user import (
    ChangeEmailForm,
    ChangePasswordForm,
    CropAvatarForm,
    DeleteAccountForm,
    EditProfileForm,
    NotificationSettingForm,
    PrivacySettingForm,
    UploadAvatarForm,
)
from app.models import Collection, Follow, Permission, Photo, User
from app.notifications import push_follow_notification
from app.utils import flash_errors, redirect_back

user = Blueprint("user", __name__)


@user.get("/<username>")
def index(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    if user == current_user and user.locked:
        flash("You account is locked.", "danger")
    if user == current_user and not user.active:
        logout_user()
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["PHOTO_PER_PAGE"]
    pagination = db.paginate(
        select(Photo).filter_by(author_id=user.id).order_by(Photo.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    photos = pagination.items
    return render_template(
        "user/index.html", user=user, pagination=pagination, photos=photos
    )


@user.get("/<username>/collections")
def show_collections(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["PHOTO_PER_PAGE"]
    pagination = db.paginate(
        user.collections.select().order_by(Collection.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    collections = pagination.items
    return render_template(
        "user/collections.html",
        user=user,
        pagination=pagination,
        collections=collections,
    )


@user.post("/follow/<username>")
@login_required
@confirm_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    if current_user.is_following(user):
        flash("Already followed.", "info")
        return redirect(url_for(".index", username=username))
    current_user.follow(user)
    flash("User followed.", "success")
    if user.receive_follow_notification:
        push_follow_notification(follower=current_user, receiver=user)
    return redirect_back()


@user.post("/unfollow/<username>")
@login_required
def unfollow(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    if not current_user.is_following(user):
        flash("Not follow yet.", "info")
        return redirect(url_for(".index", username=username))
    current_user.unfollow(user)
    flash("User unfollowed.", "info")
    return redirect_back()


@user.get("/<username>/followers")
def show_followers(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["USER_PER_PAGE"]
    pagination = db.paginate(
        user.followers.select().order_by(Follow.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    follows = pagination.items
    return render_template(
        "user/followers.html", user=user, pagination=pagination, follows=follows
    )


@user.get("/<username>/following")
def show_following(username):
    user = db.session.scalar(select(User).filter_by(username=username)) or abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["USER_PER_PAGE"]
    pagination = db.paginate(
        user.following.select().order_by(Follow.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    follows = pagination.items
    return render_template(
        "user/following.html", user=user, pagination=pagination, follows=follows
    )


@user.get("/settings/avatar")
@login_required
@confirm_required
def change_avatar():
    upload_form = UploadAvatarForm()
    crop_form = CropAvatarForm()
    return render_template(
        "user/settings/change_avatar.html", upload_form=upload_form, crop_form=crop_form
    )


@user.post("/settings/avatar/upload")
@login_required
@confirm_required
def upload_avatar():
    form = UploadAvatarForm()
    if form.validate_on_submit():
        image = form.image.data
        filename = avatars.save_avatar(image)
        current_user.avatar_raw = filename
        db.session.commit()
        flash("Image uploaded, please crop.", "success")
    flash_errors(form)
    return redirect(url_for(".change_avatar"))


@user.post("/settings/avatar/crop")
@login_required
@confirm_required
def crop_avatar():
    form = CropAvatarForm()
    if form.validate_on_submit():
        x = form.x.data
        y = form.y.data
        w = form.w.data
        h = form.h.data
        filenames = avatars.crop_avatar(current_user.avatar_raw, x, y, w, h)
        current_user.avatar_s = filenames[0]
        current_user.avatar_m = filenames[1]
        current_user.avatar_l = filenames[2]
        db.session.commit()
        flash("Avatar updated.", "success")

    flash_errors(form)
    return redirect(url_for(".change_avatar"))


@user.route("/settings/change-password", methods=["GET", "POST"])
@fresh_login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for(".index", username=current_user.username))
        else:
            flash("Old password is incorrect.", "warning")
    return render_template("user/settings/change_password.html", form=form)


@user.route("/settings/notification", methods=["GET", "POST"])
@login_required
def notification_setting():
    form = NotificationSettingForm()
    if form.validate_on_submit():
        current_user.receive_collect_notification = (
            form.receive_collect_notification.data
        )
        current_user.receive_comment_notification = (
            form.receive_comment_notification.data
        )
        current_user.receive_follow_notification = form.receive_follow_notification.data
        db.session.commit()
        flash("Notification settings updated.", "success")
        return redirect(url_for(".index", username=current_user.username))
    form.receive_collect_notification.data = current_user.receive_collect_notification
    form.receive_comment_notification.data = current_user.receive_comment_notification
    form.receive_follow_notification.data = current_user.receive_follow_notification
    return render_template("user/settings/edit_notification.html", form=form)


@user.route("/settings/privacy", methods=["GET", "POST"])
@login_required
def privacy_setting():
    form = PrivacySettingForm()
    if form.validate_on_submit():
        current_user.public_collections = form.public_collections.data
        db.session.commit()
        flash("Privacy settings updated.", "success")
        return redirect(url_for(".index", username=current_user.username))
    form.public_collections.data = current_user.public_collections
    return render_template("user/settings/edit_privacy.html", form=form)


@user.route("/settings/account/delete", methods=["GET", "POST"])
@fresh_login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        db.session.delete(current_user._get_current_object())
        db.session.commit()
        logout_user()
        flash("You are free, goodbye!", "success")
        return redirect(url_for("main.index"))
    return render_template("user/settings/delete_account.html", form=form)


@user.route("/settings/profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        current_user.website = form.website.data
        current_user.location = form.location.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for(".index", username=current_user.username))
    form.name.data = current_user.name
    form.username.data = current_user.username
    form.bio.data = current_user.bio
    form.website.data = current_user.website
    form.location.data = current_user.location
    return render_template("user/settings/edit_profile.html", form=form)


@user.route("/settings/change-email", methods=["GET", "POST"])
@fresh_login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        token = current_user.generate_token(
            operation=Operations.CHANGE_EMAIL, new_email=form.email.data.lower()
        )
        send_change_email_email(user=current_user, token=token, to=form.email.data)
        flash("Confirmation email sent, please check your inbox.", "info")
        return redirect(url_for(".index", username=current_user.username))
    return render_template("user/settings/change_email.html", form=form)


@user.get("/change-email/<token>")
@login_required
def change_email(token):
    payload = current_user.parse_token(token=token, operation=Operations.CHANGE_EMAIL)
    new_email = payload.get("new_email")
    if payload and new_email:
        current_user.email = new_email
        db.session.commit()
        flash("Email updated.", "success")
        return redirect(url_for(".index", username=current_user.username))
    else:
        flash("Invalid or expired token.", "warning")
        return redirect(url_for(".change_email_request"))
