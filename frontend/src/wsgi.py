"""WSGI entrypoint for Gunicorn.

Use a local import ("from app import app") because the working directory inside
the container is /app/frontend/src so modules live at top-level, not nested
under a package path like `frontend.src`. The previous absolute import broke
runtime startup. We keep a fallback for type-check scenarios if needed.
"""

try:  # Normal runtime path
    from app import app  # type: ignore
except ImportError:  # Fallback if executed from repo root or different PYTHONPATH
    from frontend.src.app import app  # type: ignore  # pragma: no cover

# Gunicorn looks for "application" by default when referencing module:wsgi-app
application = app
