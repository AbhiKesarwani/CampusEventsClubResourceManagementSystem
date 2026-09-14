# routes/admin.py — Coordinator Management
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from helpers.auth_helpers import admin_required
from services.user_service import (
    get_user_by_id,
    get_students_for_select,
    assign_coordinator,
    remove_coordinator,
    search_users_for_coordinator,
)
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
    """Single-page coordinator management: assign panel + directory table."""
    clubs     = get_all_clubs_with_coordinator_status()
    users     = get_students_for_select()
    directory = get_coordinator_directory()
    user      = get_user_by_id(session['user_id'])
    return render_template(
        'admin/coordinators.html',
        clubs=clubs,
        users=users,
        directory=directory,
        user=user,
        active='admin_coordinators',
    )


@bp.route('/coordinators/assign', methods=['POST'])
@admin_required
def assign():
    """Assign a user as coordinator for a club.

    Workflow
    --------
    1. Validate inputs (club exists, user exists, not admin, not same user).
    2. Demote previous coordinator (if any) → role=student, club_id=NULL.
    3. If new user already coordinates another club, clear that club first.
    4. Promote new user → role=club_admin, club_id=<this club>.
    5. Update clubs.coordinator_id / assigned_at / assigned_by.
    6. Write activity log.
    """
    club_id = request.form.get('club_id', type=int)
    user_id = request.form.get('user_id', type=int)

    if not club_id or not user_id:
        flash("Club and user are required.", "danger")
        return redirect(url_for('admin.coordinators'))

    # ── Validate club ──────────────────────────────────────────────────────────
    club = get_club_by_id(club_id)
    if not club:
        flash("Club not found.", "danger")
        return redirect(url_for('admin.coordinators'))

    # ── Validate user ──────────────────────────────────────────────────────────
    new_user = get_user_by_id(user_id)
    if not new_user:
        flash("Selected user does not exist.", "danger")
        return redirect(url_for('admin.coordinators'))

    if new_user['role'] == 'admin':
        flash("Admins cannot be assigned as club coordinators.", "danger")
        return redirect(url_for('admin.coordinators'))

    prev_coord_id = club.get('coordinator_id')
    if prev_coord_id and prev_coord_id == user_id:
        flash(f"{new_user['name']} is already the coordinator for {club['club_name']}.", "warning")
        return redirect(url_for('admin.coordinators'))

    try:
        admin_id = session['user_id']

        # ── Step 1: Demote previous coordinator ────────────────────────────────
        if prev_coord_id and prev_coord_id != user_id:
            remove_coordinator(prev_coord_id)
            log_action(admin_id, 'REMOVE_COORDINATOR', 'club', club_id,
                       f"Auto-removed previous coordinator user_id={prev_coord_id} "
                       f"before assigning user_id={user_id}")

        # ── Step 2: If new user already coords another club, clear that ────────
        if new_user.get('club_id') and new_user['club_id'] != club_id:
            old_club_id = new_user['club_id']
            set_club_coordinator(old_club_id, None, None)
            log_action(admin_id, 'CLEAR_COORDINATOR', 'club', old_club_id,
                       f"Cleared coordinator from club_id={old_club_id} "
                       f"because user_id={user_id} was reassigned")

        # ── Step 3: Promote new user ───────────────────────────────────────────
        assign_coordinator(user_id, club_id)          # users table
        set_club_coordinator(club_id, user_id, admin_id)  # clubs table

        log_action(admin_id, 'ASSIGN_COORDINATOR', 'club', club_id,
                   f"Assigned user_id={user_id} ({new_user['name']}) as coordinator")

        # Notify new coordinator (deduplicated)
        try:
            from services.notification_service import create_notification_safe
            create_notification_safe(
                user_id=user_id,
                title=f"You are now Coordinator of {club['club_name']}",
                body=(f"An admin has assigned you as Club Coordinator for {club['club_name']}. "
                      f"You can now manage events and activities for your club."),
                link=f"/clubs/{club_id}",
                type='success',
                event_key=f"coord_assigned_{club_id}_{user_id}"
            )
        except Exception:
            pass

        flash(f"✓ {new_user['name']} assigned as coordinator for {club['club_name']}.", "success")

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
            return redirect(url_for('admin.coordinators'))

        coord_id = club.get('coordinator_id')
        if coord_id:
            coord = get_user_by_id(coord_id)
            remove_coordinator(coord_id)                  # users table
            set_club_coordinator(club_id, None, None)     # clubs table
            log_action(
                session['user_id'], 'REMOVE_COORDINATOR', 'club', club_id,
                f"Removed coordinator user_id={coord_id} "
                f"({coord['name'] if coord else '?'}) from club_id={club_id}"
            )
            name = coord['name'] if coord else f"user #{coord_id}"
            flash(f"✓ {name} removed from {club['club_name']}. Role reverted to Student.", "success")
        else:
            flash("This club has no coordinator assigned.", "warning")

    except Exception as e:
        flash(f"Error removing coordinator: {e}", "danger")

    return redirect(url_for('admin.coordinators'))


# ── AJAX endpoints ─────────────────────────────────────────────────────────────

@bp.route('/coordinators/search.json')
@admin_required
def search_users_json():
    """AJAX: search users by name or email (excludes admins)."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = search_users_for_coordinator(q)
    return jsonify([{
        'user_id': u['user_id'],
        'name':    u['name'],
        'email':   u['email'],
        'role':    u['role'],
        'club_id': u['club_id'],
    } for u in results])


@bp.route('/coordinators/users.json')
@admin_required
def users_json():
    """AJAX: return all eligible users (non-admin) for assignment dropdown."""
    users = get_students_for_select()
    return jsonify([{
        'user_id': u['user_id'],
        'name':    u['name'],
        'email':   u['email'],
        'role':    u['role'],
        'club_id': u['club_id'],
    } for u in users])


@bp.route('/coordinators/clubs.json')
@admin_required
def clubs_json():
    """AJAX: return all clubs with coordinator status."""
    clubs = get_all_clubs_with_coordinator_status()
    return jsonify([{
        'club_id':           c['club_id'],
        'club_name':         c['club_name'],
        'coordinator_id':    c.get('coordinator_id'),
        'coordinator_name':  c.get('coordinator_name'),
        'coordinator_email': c.get('coordinator_email'),
        'first_image':       c.get('first_image'),
    } for c in clubs])
