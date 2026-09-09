# routes/settings.py
"""Account settings: password, profile picture, notification/AI/privacy
preferences, and session info. Reuses the same services as routes/profile.py
— no duplicate logic, just a different presentation grouped as "Settings"."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required
from helpers.upload_helpers import save_upload, delete_upload
from services.user_service import (
    get_user_by_id, update_password, update_avatar, verify_password,
    get_preferences, update_preferences
)

bp = Blueprint('settings', __name__, url_prefix='/settings')


@bp.route('/')
@login_required
def index():
    user = get_user_by_id(session['user_id'])
    if not user:
        flash("Your account could not be found. Please log in again.", "danger")
        return redirect(url_for('auth.logout'))
    return render_template(
        'settings.html',
        user=user,
        active='settings',
        preferences=get_preferences(session['user_id']),
        session_role=session.get('role'),
        session_email=session.get('email'),
        session_club_id=session.get('club_id'),
    )


@bp.route('/password', methods=['POST'])
@login_required
def change_password():
    current = request.form.get('current_password', '')
    new_pw  = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    user = get_user_by_id(session['user_id'])
    if not user or not verify_password(user, current):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for('settings.index'))
    if new_pw != confirm:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('settings.index'))

    try:
        update_password(session['user_id'], new_pw)
        flash("Password changed successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('settings.index'))


@bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if not file or not file.filename:
        flash("Please choose an image.", "danger")
        return redirect(url_for('settings.index'))
    try:
        user = get_user_by_id(session['user_id'])
        new_path = save_upload(file, prefix=f"avatar_{session['user_id']}")
        if user.get('avatar_path'):
            delete_upload(user['avatar_path'])
        update_avatar(session['user_id'], new_path)
        flash("Profile picture updated.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('settings.index'))


@bp.route('/preferences', methods=['POST'])
@login_required
def preferences():
    update_preferences(
        session['user_id'],
        notifications_enabled=request.form.get('notifications_enabled') == 'on',
        ai_response_style=request.form.get('ai_response_style', 'concise'),
        profile_visibility=request.form.get('profile_visibility', 'campus'),
    )
    flash("Preferences saved.", "success")
    return redirect(url_for('settings.index'))
