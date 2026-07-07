# routes/admin.py — Coordinator Management
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from helpers.auth_helpers import admin_required, login_required
from services.user_service import get_user_by_id, get_students_for_select, assign_coordinator, remove_coordinator
from services.club_service import (
    get_all_clubs_with_coordinator_status,
    get_coordinator_directory,
    set_club_coordinator,
    get_club_by_id,
)
from services.log_service import log_action

bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── Coordinator Management ─────────────────────────────────────────────────────

@bp.route('/coordinators')
@admin_required
def coordinators():
    clubs = get_all_clubs_with_coordinator_status()
    users = get_students_for_select()
    user  = get_user_by_id(session['user_id'])
    return render_template('admin/coordinators.html',
                           clubs=clubs, users=users,
                           user=user, active='admin_coordinators')


@bp.route('/coordinators/directory')
@admin_required
def coordinator_directory():
    directory = get_coordinator_directory()
    user      = get_user_by_id(session['user_id'])
    return render_template('admin/coordinator_directory.html',
                           directory=directory,
                           user=user, active='admin_coordinators')


@bp.route('/coordinators/assign', methods=['POST'])
@admin_required
def assign():
    """Assign a user as coordinator for a club.

    Workflow:
    1. If the club already has a coordinator → demote them to student
    2. If the new user is already a club_admin elsewhere → remove that assignment first
    3. Assign the new user as club_admin for this club
    4. Update clubs.coordinator_id
    """
    club_id  = request.form.get('club_id', type=int)
    user_id  = request.form.get('user_id', type=int)

    if not club_id or not user_id:
        flash("Club and user are required.", "danger")
        return redirect(url_for('admin.coordinators'))

    try:
        club = get_club_by_id(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('admin.coordinators'))

        # Step 1: Demote previous coordinator (if any, and different from new)
        prev_coord_id = club.get('coordinator_id')
        if prev_coord_id and prev_coord_id != user_id:
            remove_coordinator(prev_coord_id)
            log_action(session['user_id'], 'REMOVE_COORDINATOR', 'club', club_id,
                       f"Removed previous coordinator user_id={prev_coord_id}")

        # Step 2: If new user already coordinates another club, remove that
        new_user = get_user_by_id(user_id)
        if new_user and new_user.get('club_id') and new_user['club_id'] != club_id:
            set_club_coordinator(new_user['club_id'], None)

        # Step 3: Assign new coordinator
        assign_coordinator(user_id, club_id)
        set_club_coordinator(club_id, user_id)

        log_action(session['user_id'], 'ASSIGN_COORDINATOR', 'club', club_id,
                   f"Assigned user_id={user_id} as coordinator")
        flash(f"Coordinator assigned successfully!", "success")

    except Exception as e:
        flash(f"Error assigning coordinator: {e}", "danger")

    return redirect(url_for('admin.coordinators'))


@bp.route('/coordinators/remove/<int:club_id>', methods=['POST'])
@admin_required
def remove(club_id):
    """Remove coordinator from a club, reverting them to student."""
    try:
        club = get_club_by_id(club_id)
        if not club:
            flash("Club not found.", "danger")
            return redirect(url_for('admin.coordinator_directory'))

        coord_id = club.get('coordinator_id')
        if coord_id:
            remove_coordinator(coord_id)
            set_club_coordinator(club_id, None)
            log_action(session['user_id'], 'REMOVE_COORDINATOR', 'club', club_id,
                       f"Removed coordinator user_id={coord_id}")
            flash("Coordinator removed successfully.", "success")
        else:
            flash("This club has no coordinator assigned.", "warning")

    except Exception as e:
        flash(f"Error removing coordinator: {e}", "danger")

    return redirect(url_for('admin.coordinator_directory'))


# ── AJAX: users list ───────────────────────────────────────────────────────────

@bp.route('/coordinators/users.json')
@admin_required
def users_json():
    """Return all users as JSON for the assignment dropdown."""
    users = get_students_for_select()
    return jsonify(users)


@bp.route('/coordinators/clubs.json')
@admin_required
def clubs_json():
    """Return all clubs with coordinator status as JSON."""
    clubs = get_all_clubs_with_coordinator_status()
    # Convert non-serializable types
    result = []
    for c in clubs:
        result.append({
            'club_id': c['club_id'],
            'club_name': c['club_name'],
            'coordinator_id': c.get('coordinator_id'),
            'coordinator_name': c.get('coordinator_name'),
            'coordinator_email': c.get('coordinator_email'),
            'first_image': c.get('first_image'),
        })
    return jsonify(result)
