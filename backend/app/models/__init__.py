"""app/models/__init__.py — import all models here so Alembic autogenerate finds them."""
from app.models.click import ClickEvent  # noqa: F401
from app.models.url import URL  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["User", "URL", "ClickEvent"]
