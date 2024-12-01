import click
from flask import Blueprint

from app.extensions import db, whooshee

commands = Blueprint("commands", __name__, cli_group=None)


@commands.cli.command()
def initdb():
    """Create database."""
    db.drop_all()
    db.create_all()
    print("Database created.")


@commands.cli.command()
def initmail():
    """Start email server."""
    import subprocess

    print("Email server started.")
    subprocess.call(
        "aiosmtpd -n -c aiosmtpd.handlers.Debugging -l localhost:8025", shell=True
    )


@commands.cli.command()
def reindex():
    """Whooshee reindex."""
    whooshee.reindex()
    print("Whooshee reindex completed.")


@commands.cli.command()
@click.option("--user", default=10, help="Quantity of users, default is 10.")
@click.option("--follow", default=30, help="Quantity of follows, default is 30.")
@click.option("--photo", default=30, help="Quantity of photos, default is 30.")
@click.option("--tag", default=20, help="Quantity of tags, default is 20.")
@click.option("--collect", default=50, help="Quantity of collects, default is 50.")
@click.option("--comment", default=100, help="Quantity of comments, default is 100.")
def fake(user, follow, photo, tag, collect, comment):
    """Generate fake data."""
    from app.fake import (
        fake_admin,
        fake_collect,
        fake_comment,
        fake_follow,
        fake_photo,
        fake_tag,
        fake_user,
    )
    from app.models import Role

    db.drop_all()
    db.create_all()

    Role.init_roles()
    print("Roles and permissions created.")

    fake_admin()
    print("Generated the admin.")

    fake_user(user)
    print(f"Generated {user} users.")

    fake_follow(follow)
    print(f"Generated {follow} follows.")

    fake_tag(tag)
    print(f"Generated {tag} tags.")

    fake_photo(photo)
    print(f"Generated {photo} photos.")

    fake_collect(collect)
    print(f"Generated {collect} collects.")

    fake_comment(comment)
    print(f"Generated {comment} comments.")
