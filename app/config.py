import os
from enum import Enum
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Operations(Enum):
    CONFIRM = "confirm"
    RESET_PASSWORD = "reset-password"
    CHANGE_EMAIL = "change-email"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "top secret!")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@sunny.com")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = os.getenv("MAIL_PORT", 8025)

    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
    DROPZONE_MAX_FILE_SIZE = 3
    DROPZONE_MAX_FILES = 30
    DROPZONE_ALLOWED_FILE_CUSTOM = True
    DROPZONE_ALLOWED_FILE_TYPE = ".png,.jpg,.jpeg"
    DROPZONE_ENABLE_CSRF = True

    PHOTO_SIZES = {"small": 400, "medium": 800}
    PHOTO_SUFFIXES = {PHOTO_SIZES["small"]: "_s", PHOTO_SIZES["medium"]: "_m"}

    PHOTO_PER_PAGE = os.getenv("PHOTO_PER_PAGE", 5)
    USER_PER_PAGE = os.getenv("USER_PER_PAGE", 5)
    NOTIFICATION_PER_PAGE = os.getenv("NOTIFICATION_PER_PAGE", 5)
    SEARCH_RESULT_PER_PAGE = os.getenv("SEARCH_RESULT_PER_PAGE", 5)
    COMMENT_PER_PAGE = os.getenv("COMMENT_PER_PAGE", 10)

    MANAGE_USER_PER_PAGE = os.getenv("MANAGE_USER_PER_PAGE", 5)
    MANAGE_PHOTO_PER_PAGE = os.getenv("MANAGE_PHOTO_PER_PAGE", 5)
    MANAGE_TAG_PER_PAGE = os.getenv("MANAGE_TAG_PER_PAGE", 5)
    MANGE_COMMENT_PER_PAGE = os.getenv("MANGE_COMMENT_PER_PAGE", 5)

    UPLOAD_PATH = os.getenv("UPLOAD_PATH", BASE_DIR / "uploads")

    AVATARS_SAVE_PATH = UPLOAD_PATH / "avatars"
    AVATARS_SIZE_TUPLE = (30, 100, 200)


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'db-dev.sqlite'}"
    )


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite'}"
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
