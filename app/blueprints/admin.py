from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import func, select

from app.decorators import admin_required, permission_required
from app.extensions import db
from app.forms.admin import EditProfileAdminForm
from app.models import Comment, Permission, Photo, Role, Tag, User
from app.utils import redirect_back

admin = Blueprint("admin", __name__)


@admin.before_request
@login_required
@permission_required(Permission.MODERATE)
def before_admin_request():
    pass


@admin.get("/")
def index():
    user_count = db.session.scalar(select(func.count(User.id)))
    locked_user_count = db.session.scalar(
        select(func.count(User.id)).filter_by(locked=True)
    )
    blocked_user_count = db.session.scalar(
        select(func.count(User.id)).filter_by(active=True)
    )
    photo_count = db.session.scalar(select(func.count(Photo.id)))
    reported_photo_count = db.session.scalar(
        select(func.count(Photo.id)).filter(Photo.flag > 0)
    )
    tag_count = db.session.scalar(select(func.count(Tag.id)))
    comment_count = db.session.scalar(select(func.count(Comment.id)))
    reported_comment_count = db.session.scalar(
        select(func.count(Comment.id)).filter(Comment.flag > 0)
    )
    return render_template(
        "admin/index.html",
        user_count=user_count,
        photo_count=photo_count,
        tag_count=tag_count,
        comment_count=comment_count,
        locked_user_count=locked_user_count,
        blocked_user_count=blocked_user_count,
        reported_comment_count=reported_comment_count,
        reported_photo_count=reported_photo_count,
    )


@admin.post("/lock/user/<int:id>")
def lock_user(id):
    user = db.get_or_404(User, id)
    if user.role.name in []:
        flash("Permission denied.", "warning")
    else:
        user.lock()
        flash("Account locked.", "info")
    return redirect_back()


@admin.post("/unlock/user/<int:id>")
def unlock_user(id):
    user = db.get_or_404(User, id)
    user.unlock()
    flash("Lock canceled.", "info")
    return redirect_back()


@admin.route("/profile/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_profile_admin(id):
    user = db.get_or_404(User, id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.name = form.name.data
        role = db.session.get(Role, form.role.data)
        if role.name == "Locked":
            user.lock()
        user.role = role
        user.bio = form.bio.data
        user.website = form.website.data
        user.location = form.location.data
        user.username = form.username.data
        user.email = form.email.data
        user.confirmed = form.confirmed.data
        user.active = form.active.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect_back()
    form.name.data = user.name
    form.role.data = user.role_id
    form.bio.data = user.bio
    form.website.data = user.website
    form.location.data = user.location
    form.username.data = user.username
    form.email.data = user.email
    form.confirmed.data = user.confirmed
    form.active.data = user.active
    return render_template("admin/edit_profile.html", form=form, user=user)


@admin.post("/block/user/<int:id>")
def block_user(id):
    user = db.get_or_404(User, id)
    if user.role.name in ["Administrator", "Moderator"]:
        flash("Permission denied.", "warning")
    else:
        user.block()
        flash("Account blocked.", "info")
    return redirect_back()


@admin.post("/unblock/user/<int:id>")
def unblock_user(id):
    user = db.get_or_404(User, id)
    user.unblock()
    flash("Block canceled.", "info")
    return redirect_back()


@admin.route("/delete/tag/<int:id>", methods=["GET", "POST"])
def delete_tag(id):
    tag = db.get_or_404(Tag, id)
    db.session.delete(tag)
    db.session.commit()
    flash("Tag deleted.", "info")
    return redirect_back()


@admin.get("/manage/user")
def manage_user():
    filter = request.args.get("filter", "all")
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["MANAGE_USER_PER_PAGE"]
    administrator = db.session.scalar(select(Role).filter_by(name="Administrator"))
    moderator = db.session.scalar(select(Role).filter_by(name="Moderator"))

    if filter == "locked":
        filtered_users = select(User).filter_by(locked=True)
    elif filter == "blocked":
        filtered_users = select(User).filter_by(active=False)
    elif filter == "administrator":
        filtered_users = select(User).filter_by(role=administrator)
    elif filter == "moderator":
        filtered_users = select(User).filter_by(role=moderator)
    else:
        filtered_users = select(User)
    pagination = db.paginate(
        filtered_users.order_by(User.member_since.desc()), page=page, per_page=per_page
    )
    users = pagination.items
    return render_template("admin/manage_user.html", pagination=pagination, users=users)


@admin.get("/manage/photo")
@admin.get("/manage/photo/<order>")
def manage_photo(order="by_flag"):
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["MANAGE_PHOTO_PER_PAGE"]
    order_rule = "flag"
    if order == "by_time":
        pagination = db.paginate(
            select(Photo).order_by(Photo.created_at.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
        order_rule = "time"
    else:
        pagination = db.paginate(
            select(Photo).order_by(Photo.flag.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
    if page > pagination.pages:
        return redirect(
            url_for(".manage_photo", page=pagination.pages, order_rule=order_rule)
        )
    photos = pagination.items
    return render_template(
        "admin/manage_photo.html",
        pagination=pagination,
        photos=photos,
        order_rule=order_rule,
    )


@admin.get("/manage/tag")
def manage_tag():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["MANAGE_TAG_PER_PAGE"]
    pagination = db.paginate(
        select(Tag).order_by(Tag.id.desc()), page=page, per_page=per_page
    )
    tags = pagination.items
    return render_template("admin/manage_tag.html", pagination=pagination, tags=tags)


@admin.get("/manage/comment")
@admin.get("/manage/comment/<order>")
def manage_comment(order="by_flag"):
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["MANGE_COMMENT_PER_PAGE"]
    order_rule = "flag"
    if order == "by_time":
        pagination = db.paginate(
            select(Comment).order_by(Comment.created_at.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
        order_rule = "time"
    else:
        pagination = db.paginate(
            select(Comment).order_by(Comment.flag.desc()),
            page=page,
            per_page=per_page,
            error_out=False,
        )
    if page > pagination.pages:
        return redirect(url_for(".manage_comment", page=pagination.pages))
    comments = pagination.items
    return render_template(
        "admin/manage_comment.html",
        pagination=pagination,
        comments=comments,
        order_rule=order_rule,
    )


@admin.post("/delete/photo/<int:id>")
def delete_photo(id):
    photo = db.get_or_404(Photo.id)
    db.session.delete(photo)
    db.session.commit()
    flash("Photo deleted.", "info")
    return redirect_back()


@admin.post("/delete/comment/<int:id>")
def delete_comment(id):
    comment = db.get_or_404(Comment, id)
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect_back()
