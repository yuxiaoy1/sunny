from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.orm import with_parent

from app.decorators import confirm_required, permission_required
from app.extensions import db
from app.forms.main import CommentForm, DescriptionForm, TagForm
from app.models import (
    Collection,
    Comment,
    Follow,
    Notification,
    Permission,
    Photo,
    Tag,
    User,
)
from app.notifications import push_comment_notification
from app.utils import (
    allowed_file,
    flash_errors,
    random_filename,
    redirect_back,
    resize_image,
)

main = Blueprint("main", __name__)


@main.get("/")
def index():
    pagination = None
    photos = None
    if current_user.is_authenticated:
        page = request.args.get("page", 1, type=int)
        per_page = current_app.config["PHOTO_PER_PAGE"]
        pagination = db.paginate(
            select(Photo)
            .join(Follow, Follow.followed_id == Photo.author_id)
            .filter(Follow.follower_id == current_user.id)
            .order_by(Photo.created_at.desc()),
            page=page,
            per_page=per_page,
        )
        photos = pagination.items
    tags = db.session.scalars(
        select(Tag)
        .join(Tag.photos)
        .group_by(Tag.id)
        .order_by(func.count(Photo.id).desc())
        .limit(10)
    )
    return render_template(
        "main/index.html", pagination=pagination, photos=photos, tags=tags
    )


@main.get("/explore")
def explore():
    photos = db.session.scalars(select(Photo).order_by(func.random()).limit(10))
    return render_template("main/explore.html", photos=photos)


@main.get("/search")
def search():
    q = request.args.get("q").strip()
    if not q:
        flash("Enter keyword about photo, user or tag.", "warning")
        redirect_back()
    category = request.args.get("category", "photo")
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["SEARCH_RESULT_PER_PAGE"]
    if category == "user":
        pagination = User.query.whooshee_search(q).paginate(
            page=page, per_page=per_page
        )
    elif category == "tag":
        pagination = Tag.query.whooshee_search(q).paginate(page=page, per_page=per_page)
    else:
        pagination = Photo.query.whooshee_search(q).paginate(
            page=page, per_page=per_page
        )
    results = pagination.items
    return render_template(
        "main/search.html",
        q=q,
        results=results,
        pagination=pagination,
        category=category,
    )


@main.route("/upload", methods=["GET", "POST"])
@login_required
@confirm_required
@permission_required(Permission.UPLOAD)
def upload():
    if request.method == "POST":
        if "file" not in request.files:
            return "No image.", 400
        f = request.files.get("file")
        if not allowed_file(f.filename):
            return "Invalid image.", 400
        filename = random_filename(f.filename)
        f.save(current_app.config["UPLOAD_PATH"] / filename)
        filename_s = resize_image(
            f, filename, current_app.config["PHOTO_SIZES"]["small"]
        )
        filename_m = resize_image(
            f, filename, current_app.config["PHOTO_SIZES"]["medium"]
        )
        photo = Photo(
            filename=filename,
            filename_s=filename_s,
            filename_m=filename_m,
            author=current_user._get_current_object(),
        )
        db.session.add(photo)
        db.session.commit()
    return render_template("main/upload.html")


@main.get("/avatars/<path:filename>")
def get_avatar(filename):
    return send_from_directory(current_app.config["AVATARS_SAVE_PATH"], filename)


@main.get("/images/<path:filename>")
def get_image(filename):
    return send_from_directory(current_app.config["UPLOAD_PATH"], filename)


@main.get("/photo/<int:id>")
def show_photo(id):
    photo = db.get_or_404(Photo, id)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["COMMENT_PER_PAGE"]
    pagination = db.paginate(
        select(Comment).filter_by(photo_id=photo.id).order_by(Comment.created_at.asc()),
        page=page,
        per_page=per_page,
    )
    comments = pagination.items
    comment_form = CommentForm()
    tag_form = TagForm()
    description_form = DescriptionForm()
    description_form.description.data = photo.description
    return render_template(
        "main/photo.html",
        photo=photo,
        description_form=description_form,
        comment_form=comment_form,
        tag_form=tag_form,
        pagination=pagination,
        comments=comments,
    )


@main.get("/photo/n/<int:id>")
def get_next_photo(id):
    photo = db.get_or_404(Photo, id)
    next_photo = db.session.scalar(
        select(Photo)
        .filter(
            with_parent(photo.author, User.photos), Photo.created_at < photo.created_at
        )
        .order_by(Photo.created_at.desc())
    )
    if next_photo is None:
        flash("This is already the last one.", "info")
        return redirect(url_for(".show_photo", id=id))
    return redirect(url_for(".show_photo", id=next_photo.id))


@main.get("/photo/p/<int:id>")
def get_previous_photo(id):
    photo = db.get_or_404(Photo, id)
    previous_photo = db.session.scalar(
        select(Photo)
        .filter(
            with_parent(photo.author, User.photos), Photo.created_at > photo.created_at
        )
        .order_by(Photo.created_at.asc())
    )
    if previous_photo is None:
        flash("This is already the first one.", "info")
        return redirect(url_for(".show_photo", id=id))
    return redirect(url_for(".show_photo", id=previous_photo.id))


@main.route("/delete/photo/<int:id>", methods=["GET", "POST"])
@login_required
def delete_photo(id):
    photo = db.get_or_404(Photo, id)
    if current_user != photo.author and not current_user.can(Permission.MODERATE):
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    flash("Photo deleted.", "info")
    query = select(Photo).filter(Photo.author_id == photo.author_id)
    next_photo = db.session.scalar(
        query.filter(Photo.created_at < photo.created_at).order_by(
            Photo.created_at.desc()
        )
    )
    if next_photo is None:
        previous_photo = db.session.scalar(
            query.filter(Photo.created_at > photo.created_at).order_by(
                Photo.created_at.asc()
            )
        )
        if previous_photo is None:
            return redirect(url_for("user.index", username=photo.author.username))
        return redirect(url_for(".show_photo", id=previous_photo.id))
    return redirect(url_for(".show_photo", id=next_photo.id))


@main.route("/report/photo/<int:id>", methods=["GET", "POST"])
@login_required
@confirm_required
def report_photo(id):
    photo = db.get_or_404(Photo, id)
    photo.flag += 1
    db.session.commit()
    flash("Photo reported.", "success")
    return redirect(url_for(".show_photo", id=photo.id))


@main.route("/photo/<int:id>/description", methods=["GET", "POST"])
@login_required
def edit_description(id):
    photo = db.get_or_404(Photo, id)
    if current_user != photo.author:
        abort(403)
    form = DescriptionForm()
    if form.validate_on_submit():
        photo.description = form.description.data
        db.session.commit()
        flash("Description updated.", "success")
    flash_errors(form)
    return redirect(url_for(".show_photo", id=photo.id))


@main.route("/photo/<int:id>/tag/new", methods=["GET", "POST"])
@login_required
def new_tag(id):
    photo = db.get_or_404(Photo, id)
    if current_user != photo.author:
        abort(403)
    form = TagForm()
    if form.validate_on_submit():
        for name in form.tag.data.split():
            tag = db.session.scalar(select(Tag).filter_by(name=name))
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.commit()
            if tag not in photo.tags:
                photo.tags.append(tag)
                db.session.commit()
        flash("Tag added.", "success")
    flash_errors(form)
    return redirect(url_for(".show_photo", id=photo.id))


@main.route("/delete/tag/<int:photo_id>/<int:tag_id>", methods=["GET", "POST"])
@login_required
def delete_tag(photo_id, tag_id):
    photo = db.get_or_404(Photo, photo_id)
    tag = db.get_or_404(Tag, tag_id)
    if current_user != photo.author:
        abort(403)
    photo.tags.remove(tag)
    db.session.commit()
    tag_photos = db.session.scalars(tag.photos.select()).all()
    if not tag_photos:
        db.session.delete(tag)
        db.session.commit()
    flash("Tag deleted.", "info")
    return redirect(url_for(".show_photo", id=photo_id))


@main.get("/tag/<int:id>")
def show_tag(id):
    tag = db.get_or_404(Tag, id)
    page = request.args.get("page", 1, type=int)
    order_rule = request.args.get("order_rule", "time")
    per_page = current_app.config["PHOTO_PER_PAGE"]
    pagination = db.paginate(
        tag.photos.select().order_by(Photo.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    photos = pagination.items
    if order_rule == "collections":
        photos.sort(key=lambda x: x.collectors_count, reverse=True)
    return render_template(
        "main/tag.html",
        tag=tag,
        pagination=pagination,
        photos=photos,
        order_rule=order_rule,
    )


@main.post("/collect/<int:id>")
@login_required
@confirm_required
@permission_required(Permission.COLLECT)
def collect(id):
    photo = db.get_or_404(Photo, id)
    if current_user.is_collecting(photo):
        flash("Already collected.", "info")
    else:
        current_user.collect(photo)
        flash("Photo collected.", "success")
    return redirect(url_for(".show_photo", id=photo.id))


@main.post("/uncollect/<int:id>")
@login_required
def uncollect(id):
    photo = db.get_or_404(Photo, id)
    if not current_user.is_collecting(photo):
        flash("Not collect yet.", "info")
    else:
        current_user.uncollect(photo)
        flash("Photo uncollected.", "info")
    return redirect(url_for(".show_photo", id=photo.id))


@main.get("/photo/<int:id>/collectors")
def show_collectors(id):
    photo = db.get_or_404(Photo, id)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["USER_PER_PAGE"]
    pagination = db.paginate(
        photo.collections.select().order_by(Collection.created_at.desc()),
        page=page,
        per_page=per_page,
    )
    collections = pagination.items
    return render_template(
        "main/collectors.html",
        collections=collections,
        photo=photo,
        pagination=pagination,
    )


@main.get("/notifications")
@login_required
def show_notifications():
    page = request.args.get("page", 1, type=int)
    filter_rule = request.args.get("filter")
    per_page = current_app.config["NOTIFICATION_PER_PAGE"]
    query = current_user.notifications.select()
    if filter_rule == "unread":
        query = query.filter_by(is_read=False)
    pagination = db.paginate(
        query.order_by(Notification.created_at.desc()), page=page, per_page=per_page
    )
    notifications = pagination.items
    return render_template(
        "main/notifications.html", pagination=pagination, notifications=notifications
    )


@main.post("/notifications/read/<int:id>")
@login_required
def read_notification(id):
    notification = db.get_or_404(Notification, id)
    if current_user != notification.receiver:
        abort(403)
    notification.is_read = True
    db.session.commit()
    flash("Notification archived.", "success")
    return redirect(url_for(".show_notifications"))


@main.post("/notifications/read/all")
@login_required
def read_all_notification():
    notifications = db.session.scalars(
        current_user.notifications.select().filter_by(is_read=False)
    )
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    flash("All notification archived.", "success")
    return redirect(url_for(".show_notifications"))


@main.post("/report/comment/<int:id>")
@login_required
@confirm_required
def report_comment(id):
    comment = db.get_or_404(Comment, id)
    comment.flag += 1
    db.session.commit()
    flash("Comment reported.", "success")
    return redirect(url_for(".show_photo", id=comment.photo_id))


@main.post("/photo/<int:id>/comment/new")
@login_required
@permission_required(Permission.COMMENT)
def new_comment(id):
    photo = db.get_or_404(Photo, id)
    page = request.args.get("page", 1, type=int)
    form = CommentForm()
    if form.validate_on_submit():
        body = form.body.data
        author = current_user._get_current_object()
        comment = Comment(body=body, author=author, photo=photo)
        replied_id = request.args.get("reply")
        if replied_id:
            comment.replied = db.get_or_404(Comment, replied_id)
            if comment.replied.author.receive_comment_notification:
                push_comment_notification(
                    photo_id=photo.id, receiver=comment.replied.author
                )
        db.session.add(comment)
        db.session.commit()
        flash("Comment publised.", "success")
        if current_user != photo.author and photo.author.receive_comment_notification:
            push_comment_notification(id, receiver=photo.author, page=page)
    flash_errors(form)
    return redirect(url_for(".show_photo", id=id, page=page))


@main.post("/set-comment/<int:id>")
@login_required
def set_comment(id):
    photo = db.get_or_404(Photo, id)
    if current_user != photo.author:
        abort(403)
    if photo.can_comment:
        photo.can_comment = False
        flash("Comment disabled.", "info")
    else:
        photo.can_comment = True
        flash("Comment enabled.", "info")
    db.session.commit()
    return redirect(url_for(".show_photo", id=id))


@main.get("/reply/comment/<int:id>")
@login_required
@permission_required(Permission.COMMENT)
def reply_comment(id):
    comment = db.get_or_404(Comment, id)
    return redirect(
        url_for(
            ".show_photo", id=comment.photo_id, reply=id, author=comment.author.name
        )
        + "#comment-form"
    )


@main.post("/delete/comment/<int:id>")
@login_required
def delete_comment(id):
    comment = db.get_or_404(Comment, id)
    if (
        current_user != comment.author
        and current_user != comment.photo.author
        and not current_user.can(Permission.MODERATE)
    ):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect(
        url_for(
            ".show_photo",
            id=comment.photo_id,
        )
    )
