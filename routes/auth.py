# routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from services.user_service import get_user_by_email, create_user, verify_password, update_password

bp = Blueprint('auth', __name__)

RESET_SALT = 'campusops-password-reset-salt'
RESET_MAX_AGE = 1800  # 30 minutes


def _get_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get('SECRET_KEY', 'dev-secret-key-campusops-2026')
    return URLSafeTimedSerializer(secret)


def generate_reset_token(email: str) -> str:
    s = _get_serializer()
    return s.dumps(email.lower().strip(), salt=RESET_SALT)


def verify_reset_token(token: str, max_age: int = RESET_MAX_AGE) -> str | None:
    s = _get_serializer()
    try:
        email = s.loads(token, salt=RESET_SALT, max_age=max_age)
        return str(email)
    except (SignatureExpired, BadTimeSignature, Exception):
        return None


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
            session['user_id']     = user['user_id']
            session['role']        = user['role']
            session['name']        = user['name']
            session['email']       = user['email']
            session['club_id']     = user.get('club_id')
            session['avatar_path'] = user.get('avatar_path')
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard.index'))
        flash("Invalid email or password.", "danger")
    return render_template('login.html', user=None)


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash("Please enter your registered email address.", "danger")
            return render_template('forgot_password.html')

        user = get_user_by_email(email)
        if user:
            token = generate_reset_token(user['email'])
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            flash(f"Password reset link generated: <a href='{reset_url}' style='color:var(--primary);font-weight:700;text-decoration:underline;'>Click here to reset your password</a> (valid for 30 minutes)", "info")
        else:
            flash("If an account exists with that email, password reset instructions have been sent.", "info")
        return render_template('forgot_password.html')

    return render_template('forgot_password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    email = verify_reset_token(token)
    if not email:
        flash("The password reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for('auth.forgot_password'))

    user = get_user_by_email(email)
    if not user:
        flash("User account not found.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not password or len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('reset_password.html', token=token, email=email)

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template('reset_password.html', token=token, email=email)

        try:
            update_password(user['user_id'], password)
            flash("Your password has been successfully reset! Please sign in with your new password.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f"Error resetting password: {e}", "danger")
            return render_template('reset_password.html', token=token, email=email)

    return render_template('reset_password.html', token=token, email=email)


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

