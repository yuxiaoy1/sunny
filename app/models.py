from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from flask_avatars import Identicon
from flask_login import UserMixin
from jwt.exceptions import InvalidTokenError
from sqlalchemy import Column, ForeignKey, String, Text, engine, event, func, select
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, whooshee


class Follow(db.Model):
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    followed_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    follower: Mapped["User"] = relationship(
        foreign_keys=[follower_id], back_populates="following", lazy="joined"
    )
    followed: Mapped["User"] = relationship(
        foreign_keys=[followed_id], back_populates="followers", lazy="joined"
    )


@whooshee.register_model("username", "name")
class User(db.Model, UserMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(50))
    member_since: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    confirmed: Mapped[bool] = mapped_column(default=False)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("role.id"))
    role: Mapped["Role"] = relationship(back_populates="users")
    photos: WriteOnlyMapped[["Photo"]] = relationship(
        back_populates="author", cascade="all, delete-orphan", passive_deletes=True
    )
    avatar_s: Mapped[str | None] = mapped_column(String(64))
    avatar_m: Mapped[str | None] = mapped_column(String(64))
    avatar_l: Mapped[str | None] = mapped_column(String(64))
    avatar_raw: Mapped[str | None] = mapped_column(String(64))
    collections: WriteOnlyMapped["Collection"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    following: WriteOnlyMapped["Follow"] = relationship(
        foreign_keys=[Follow.follower_id],
        back_populates="follower",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    followers: WriteOnlyMapped["Follow"] = relationship(
        foreign_keys=[Follow.followed_id],
        back_populates="followed",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: WriteOnlyMapped["Notification"] = relationship(
        back_populates="receiver", cascade="all, delete-orphan", passive_deletes=True
    )
    receive_comment_notification: Mapped[bool] = mapped_column(default=True)
    receive_follow_notification: Mapped[bool] = mapped_column(default=True)
    receive_collect_notification: Mapped[bool] = mapped_column(default=True)
    public_collections: Mapped[bool] = mapped_column(default=True)
    comments: WriteOnlyMapped["Comment"] = relationship(
        back_populates="author", cascade="all, delete-orphan", passive_deletes=True
    )
    locked: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_role()
        self.generate_avatar()
        self.follow(self)

    @property
    def password(self):
        raise AttributeError("Write-only property!")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self, operation, expires_in=3600, **kwargs):
        payload = {
            "id": self.id,
            "operation": operation.value,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }
        payload.update(**kwargs)
        return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

    def parse_token(self, token, operation):
        try:
            payload = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
        except InvalidTokenError:
            return {}
        if operation.value != payload.get("operation") or self.id != payload.get("id"):
            return {}
        return payload

    def set_role(self):
        if self.role is None:
            role_name = (
                "Admin" if self.email == current_app.config["ADMIN_EMAIL"] else "User"
            )
            self.role = db.session.scalar(select(Role).filter_by(name=role_name))

    @property
    def is_admin(self):
        return self.can(Permission.ADMIN)

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def generate_avatar(self):
        avatar = Identicon()
        self.avatar_s, self.avatar_m, self.avatar_l = avatar.generate(
            text=self.username
        )

    def collect(self, photo):
        if not self.is_collecting(photo):
            collection = Collection(user=self, photo=photo)
            db.session.add(collection)
            db.session.commit()

    def uncollect(self, photo):
        collection = db.session.scalar(
            self.collections.select().filter_by(photo_id=photo.id)
        )
        if collection:
            db.session.delete(collection)
            db.session.commit()

    def is_collecting(self, photo):
        return (
            db.session.scalar(self.collections.select().filter_by(photo_id=photo.id))
            is not None
        )

    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()

    def unfollow(self, user):
        follow = db.session.scalar(
            self.following.select().filter_by(followed_id=user.id)
        )
        if follow:
            db.session.delete(follow)
            db.session.commit()

    def is_following(self, user):
        return user.id and db.session.scalar(
            self.following.select().filter_by(followed_id=user.id)
        )

    def is_followed_by(self, user):
        return (
            db.session.scalar(self.followers.select().filter_by(followed_id=user.id))
            is not None
        )

    @staticmethod
    def follow_self_all():
        for user in db.session.scalars(select(User)):
            user.follow(user)
        db.session.commit()

    @property
    def followers_count(self):
        return (
            db.session.scalar(self.followers.select().with_only_columns(func.count()))
            - 1
        )

    @property
    def following_count(self):
        return (
            db.session.scalar(self.following.select().with_only_columns(func.count()))
            - 1
        )

    def lock(self):
        self.locked = True
        self.role = db.session.scalar(select(Role).filter_by(name="Locked"))
        db.session.commit()

    def unlock(self):
        self.locked = False
        self.role = db.session.scalar(select(Role).filter_by(name="User"))
        db.session.commit()

    @property
    def is_active(self):
        return self.active

    def block(self):
        self.active = False
        db.session.commit()

    def unblock(self):
        self.active = True
        db.session.commit()


class Permission:
    FOLLOW = 1
    COLLECT = 2
    COMMENT = 4
    UPLOAD = 8
    MODERATE = 16
    ADMIN = 32


class Role(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    default: Mapped[bool] = mapped_column(default=False, index=True)
    permissions: Mapped[int] = mapped_column(default=0)
    users: WriteOnlyMapped["User"] = relationship(
        back_populates="role", passive_deletes=True
    )

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def init_roles():
        roles = {
            "Locked": [Permission.FOLLOW, Permission.COLLECT],
            "User": [
                Permission.FOLLOW,
                Permission.COLLECT,
                Permission.COMMENT,
                Permission.UPLOAD,
            ],
            "Moderator": [
                Permission.FOLLOW,
                Permission.COLLECT,
                Permission.COMMENT,
                Permission.UPLOAD,
                Permission.MODERATE,
            ],
            "Admin": [
                Permission.FOLLOW,
                Permission.COLLECT,
                Permission.COMMENT,
                Permission.UPLOAD,
                Permission.MODERATE,
                Permission.ADMIN,
            ],
        }
        default_role = "User"
        for r in roles:
            role = db.session.scalar(select(Role).filter_by(name=r))
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = role.name == default_role
            db.session.add(role)
        db.session.commit()


photo_tag = db.Table(
    "photo_tag",
    Column("photo_id", ForeignKey("photo.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


@whooshee.register_model("description")
class Photo(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str | None] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), index=True
    )
    can_comment: Mapped[bool] = mapped_column(default=True)
    flag: Mapped[int] = mapped_column(default=0)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    author: Mapped["User"] = relationship(back_populates="photos")
    filename: Mapped[str] = mapped_column(String(64))
    filename_s: Mapped[str] = mapped_column(String(64))
    filename_m: Mapped[str] = mapped_column(String(64))
    tags: Mapped[list["Tag"]] = relationship(
        secondary=photo_tag, back_populates="photos", passive_deletes=True
    )
    collections: WriteOnlyMapped["Collection"] = relationship(
        back_populates="photo", cascade="all, delete-orphan", passive_deletes=True
    )
    comments: WriteOnlyMapped["Comment"] = relationship(
        back_populates="photo", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def collectors_count(self):
        return db.session.scalar(
            select(func.count(Collection.user_id)).filter_by(user_id=self.id)
        )


@whooshee.register_model("name")
class Tag(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    photos: WriteOnlyMapped["Photo"] = relationship(
        secondary=photo_tag, back_populates="tags", passive_deletes=True
    )


class Collection(db.Model):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("photo.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    user: Mapped["User"] = relationship(back_populates="collections", lazy="joined")
    photo: Mapped["Photo"] = relationship(back_populates="collections", lazy="joined")


class Notification(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), index=True
    )
    receiver_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    receiver: Mapped["User"] = relationship(back_populates="notifications")


class Comment(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    flag: Mapped[int] = mapped_column(default=0)
    replied_id: Mapped[int | None] = mapped_column(
        ForeignKey("comment.id", ondelete="CASCADE")
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    photo_id: Mapped[int] = mapped_column(ForeignKey("photo.id", ondelete="CASCADE"))
    replies: WriteOnlyMapped["Comment"] = relationship(
        back_populates="replied", cascade="all, delete-orphan", passive_deletes=True
    )
    replied: Mapped["Comment"] = relationship(
        back_populates="replies", remote_side=[id]
    )
    photo: Mapped["Photo"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


@event.listens_for(engine.Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    import sqlite3

    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(Photo, "after_delete", named=True)
def delete_photos(**kwargs):
    target = kwargs["target"]
    for filename in [target.filename, target.filename_s, target.filename_m]:
        path = current_app.config["UPLOAD_PATH"] / filename
        if path.exists():
            path.unlink()


@event.listens_for(User, "after_delete", named=True)
def delete_avatars(**kwargs):
    target = kwargs["target"]
    for filename in [
        target.avatar_s,
        target.avatar_m,
        target.avatar_l,
        target.avatar_raw,
    ]:
        if filename is not None:
            path = current_app.config["AVATARS_SAVE_PATH"] / filename
            if path.exists():
                path.unlink()
