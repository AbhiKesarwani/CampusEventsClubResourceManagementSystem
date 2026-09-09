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
