# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.user_service import get_user_by_email, create_user, verify_password, get_all_users
from services.club_service import get_clubs_for_select
from helpers.auth_helpers import login_required

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pw    = request.form.get('password', '')
        user  = get_user_by_email(email)
        if user and verify_password(user, pw):
            session.clear()
            session['user_id'] = user['user_id']
            session['role']    = user['role']
            session['name']    = user['name']
            session['email']   = user['email']
            session['club_id'] = user.get('club_id')
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard.index'))
        flash("Invalid email or password.", "danger")
    return render_template('login.html', user=None)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        # club_id intentionally NOT accepted from form — assigned by coordinator only

        if not (name and email and password):
            flash("Name, email, and password are required.", "danger")
            return render_template('register.html', user=None)
        try:
            create_user(name, email, password, phone, club_id=None, role='student')
            flash("Registered successfully. Please login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
    return render_template('register.html', user=None)


@bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('auth.login'))
