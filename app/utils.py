from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from flask import current_app, flash, redirect, request, url_for
from PIL import Image


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def redirect_back(default="blog.index", **kwargs):
    for target in request.args.get("next"), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return redirect(target)
    return redirect(url_for(default, **kwargs))


def random_filename(filename):
    return uuid4().hex + Path(filename).suffix


def allowed_file(filename):
    return (
        "." in filename
        and Path(filename).suffix.lower()
        in current_app.config["DROPZONE_ALLOWED_FILE_TYPE"]
    )


def resize_image(image, filename, base_width):
    ext = Path(filename).suffix
    img = Image.open(image)
    if img.size[0] <= base_width:
        return filename + ext
    w_percent = base_width / float(img.size[0])
    h_size = int(float(img.size[1]) * float(w_percent))
    img = img.resize((base_width, h_size), Image.LANCZOS)

    filename += current_app.config["PHOTO_SUFFIXES"][base_width] + ext
    img.save(current_app.config["UPLOAD_PATH"] / filename, optimize=True, quality=85)
    return filename


def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"Error in the {getattr(form, field).label.text} field - {error}")
