# routes/profile.py
"""Modern profile page: avatar, role-specific info, joined clubs,
achievements, attendance/certificates, recent activity, and a personal
timeline. Reuses existing services — no duplicate queries."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required
from helpers.upload_helpers import save_upload, delete_upload
from services.user_service import (
    get_user_by_id, update_profile, update_password, update_avatar, verify_password
)
from services.attendance_service import get_user_attendance
from services.certificate_service import get_user_certificates
from services.member_service import get_clubs_for_user
from services.club_service import get_club_by_id
from services.log_service import get_recent_activity
from services.connect_service import count_unread_messages

bp = Blueprint('profile', __name__, url_prefix='/profile')


def _build_achievements(attended: list, certs: list, clubs: list) -> list[dict]:
    """Derive simple achievement badges from existing data (no new tables)."""
    badges = []
    if attended:
        badges.append({'icon': 'check-circle', 'label': 'First Event Attended', 'color': 'emerald'})
    if len(attended) >= 5:
        badges.append({'icon': 'flame', 'label': '5+ Events Attended', 'color': 'amber'})
    if len(attended) >= 10:
        badges.append({'icon': 'trophy', 'label': '10+ Events Attended', 'color': 'purple'})
    if certs:
        badges.append({'icon': 'award', 'label': 'First Certificate Earned', 'color': 'emerald'})
    if len(certs) >= 3:
        badges.append({'icon': 'medal', 'label': 'Certificate Collector', 'color': 'amber'})
    if any(c.get('position') in ('President', 'Vice President', 'Secretary', 'Treasurer') for c in clubs):
        badges.append({'icon': 'crown', 'label': 'Club Leadership', 'color': 'purple'})
    if len(clubs) >= 2:
        badges.append({'icon': 'users', 'label': 'Multi-Club Member', 'color': 'blue'})
    return badges


@bp.route('/')
@login_required
def index():
    return view_profile(session['user_id'])


@bp.route('/<int:user_id>')
@login_required
def view_profile(user_id):
    """View a profile. Everyone can view their own; admin/coordinator can
    view others (coordinators limited to their own club's members via a
    lightweight check, since full profiles include attendance/certs)."""
    viewer_id   = session['user_id']
    viewer_role = session.get('role')

    if user_id != viewer_id and viewer_role not in ('admin', 'club_admin'):
        flash("You can only view your own profile.", "danger")
        return redirect(url_for('profile.index'))

    target = get_user_by_id(user_id)
    if not target:
        flash("User not found.", "danger")
        return redirect(url_for('dashboard.index'))

    if user_id != viewer_id and viewer_role == 'club_admin':
        from services.member_service import is_member
        my_club_id = session.get('club_id')
        if not my_club_id or not is_member(my_club_id, user_id):
            flash("You can only view profiles of your own club's members.", "danger")
            return redirect(url_for('profile.index'))

    attended = get_user_attendance(user_id)
    certs    = get_user_certificates(user_id)
    clubs    = get_clubs_for_user(user_id)
    activity = get_recent_activity(limit=8, user_id=user_id)
    is_own   = (user_id == viewer_id)

    ctx = dict(
        user=get_user_by_id(viewer_id),
        active='profile',
        profile_user=target,
        is_own_profile=is_own,
        attended=attended,
        certificates=certs,
        clubs=clubs,
        activity=activity,
        achievements=_build_achievements(attended, certs, clubs),
        stat_attended=len(attended),
        stat_certificates=len(certs),
        stat_clubs=len(clubs),
    )
    if is_own:
        ctx['unread_messages'] = count_unread_messages(viewer_id)
        if target.get('club_id'):
            ctx['coordinating_club'] = get_club_by_id(target['club_id'])

    return render_template('profile.html', **ctx)


@bp.route('/edit', methods=['POST'])
@login_required
def edit():
    try:
        update_profile(session['user_id'], request.form.get('name', ''), request.form.get('phone', ''))
        session['name'] = request.form.get('name', session.get('name'))
        flash("Profile updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('profile.index'))


@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current  = request.form.get('current_password', '')
    new_pw   = request.form.get('new_password', '')
    confirm  = request.form.get('confirm_password', '')

    user = get_user_by_id(session['user_id'])
    if not user or not verify_password(user, current):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for('profile.index'))
    if new_pw != confirm:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('profile.index'))

    try:
        update_password(session['user_id'], new_pw)
        flash("Password changed successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('profile.index'))


@bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    file = request.files.get('avatar')
    if not file or not file.filename:
        flash("Please choose an image.", "danger")
        return redirect(url_for('profile.index'))
    try:
        user = get_user_by_id(session['user_id'])
        new_path = save_upload(file, prefix=f"avatar_{session['user_id']}")
        if user.get('avatar_path'):
            delete_upload(user['avatar_path'])
        update_avatar(session['user_id'], new_path)
        flash("Profile picture updated.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for('profile.index'))
