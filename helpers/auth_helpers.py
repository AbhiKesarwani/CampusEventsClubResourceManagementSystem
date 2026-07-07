# helpers/auth_helpers.py
from functools import wraps
from flask import session, redirect, url_for, flash


# ─────────────────────────────────────────────────────────────
# Basic guards
# ─────────────────────────────────────────────────────────────

def login_required(fn):
    """Redirect to login if user is not authenticated."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "danger")
            return redirect(url_for('auth.login'))
        return fn(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """Allow access only if the logged-in user has one of the specified roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please login first.", "danger")
                return redirect(url_for('auth.login'))
            if session.get('role') not in allowed_roles:
                flash("Access denied: insufficient privileges.", "danger")
                return redirect(url_for('dashboard.index'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Restrict route to admin only."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "danger")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('dashboard.index'))
        return fn(*args, **kwargs)
    return wrapper


def club_admin_required(fn):
    """Restrict route to club_admin or admin."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "danger")
            return redirect(url_for('auth.login'))
        if session.get('role') not in ('admin', 'club_admin'):
            flash("Club admin access required.", "danger")
            return redirect(url_for('dashboard.index'))
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────
# Email-based Club Ownership
# ─────────────────────────────────────────────────────────────

def is_club_owner(club_email: str | None) -> bool:
    """
    Returns True if the current session user owns the club.

    Ownership model:
    - admin always owns every club.
    - club_admin owns a club if their email == club.club_email
      (club_email set by admin when creating/editing the club).
    - student never owns a club.

    Args:
        club_email: The club's registered email address (from DB).

    Usage (in routes):
        club = get_club_by_id(club_id)
        if not is_club_owner(club['club_email']):
            flash("Not your club.", "danger")
            return redirect(url_for('dashboard.index'))
    """
    role = session.get('role')
    if role == 'admin':
        return True
    if role == 'club_admin':
        user_email = session.get('email', '')
        return bool(club_email and user_email and
                    club_email.strip().lower() == user_email.strip().lower())
    return False


def club_owner_or_admin(get_club_email_fn):
    """
    Decorator: restrict write operations so that:
    - admin can do anything
    - club_admin can only operate on clubs they own (email match)

    The argument is a callable that returns the club's email.
    Call it with a lambda that fetches the club record.

    Usage:
        @club_owner_or_admin(lambda: get_club_by_id(
            request.view_args['club_id'])['club_email'])
        def edit(club_id): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please login first.", "danger")
                return redirect(url_for('auth.login'))
            role = session.get('role')
            if role == 'admin':
                return fn(*args, **kwargs)
            if role == 'club_admin':
                club_email = get_club_email_fn()
                if is_club_owner(club_email):
                    return fn(*args, **kwargs)
                flash("You can only manage your own club.", "danger")
                return redirect(url_for('dashboard.index'))
            flash("Access denied.", "danger")
            return redirect(url_for('dashboard.index'))
        return wrapper
    return decorator
