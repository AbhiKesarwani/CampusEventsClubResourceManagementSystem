# routes/clubs.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from helpers.auth_helpers import (
    login_required, admin_required, club_admin_required
)
from helpers.upload_helpers import save_upload, delete_upload
from services.user_service import get_user_by_id
from services.club_service import (
    get_all_clubs, count_all_clubs, get_club_by_id, get_club_images,
    create_club, update_club, delete_club,
    add_club_image, delete_club_image
)
from services.member_service import (
    get_club_members, add_member, remove_member, change_position,
    get_non_members
)
from services.membership_service import (
    get_requests_for_club, approve_request, reject_request,
    count_pending_requests_for_club
)
from services.event_service import get_upcoming_events
from services.log_service import log_action

bp = Blueprint('clubs', __name__, url_prefix='/clubs')

POSITIONS = ['President', 'Vice President', 'Secretary', 'Treasurer',
             'Coordinator', 'Volunteer', 'Member']

PER_PAGE = 12


# ── Ownership helper (coordinator_id-based) ────────────────────────────────────
def _can_manage_club(club_id: int) -> bool:
    """True if current user is admin OR is the assigned coordinator of this club."""
    role = session.get('role')
    if role == 'admin':
        return True
    if role == 'club_admin':
        return session.get('club_id') == club_id
    return False


# ── List ───────────────────────────────────────────────────────────────────────
@bp.route('/')
@login_required
def list_clubs():
    search = request.args.get('search', '').strip()
    page   = request.args.get('page', 1, type=int)

    total       = count_all_clubs(search=search or None)
    per_page    = PER_PAGE
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(1, min(page, total_pages))
    offset      = (page - 1) * per_page

    clubs = get_all_clubs(search=search or None)
    # Paginate in-memory (dataset is small; service returns all matching)
    clubs = clubs[offset: offset + per_page]

    user = get_user_by_id(session['user_id'])
    return render_template('clubs/list.html',
                           clubs=clubs,
                           user=user, active='clubs',
                           page=page, total_pages=total_pages, total=total,
                           filters={'search': search})


# ── Detail ─────────────────────────────────────────────────────────────────────
@bp.route('/<int:club_id>')
@login_required
def detail(club_id):
    club = get_club_by_id(club_id)
    if not club:
        flash("Club not found.", "danger")
        return redirect(url_for('clubs.list_clubs'))

    images  = get_club_images(club_id)
    members = get_club_members(club_id)
    user    = get_user_by_id(session['user_id'])

    # Ownership check uses coordinator_id-based logic
    can_manage = _can_manage_club(club_id)
    role = session.get('role')

    pending_count = 0
    if can_manage or role == 'admin':
        pending_count = count_pending_requests_for_club(club_id)

    # Upcoming events for this club
    upcoming = get_upcoming_events(limit=4, club_id=club_id)

    return render_template('clubs/detail.html',
                           club=club,
                           club_images=images,
                           members=members,
                           can_manage=can_manage,
                           pending_count=pending_count,
                           upcoming_events=upcoming,
                           user=user, active='clubs')


# ── Create ─────────────────────────────────────────────────────────────────────
@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    if request.method == 'POST':
        name       = request.form.get('club_name', '').strip()
        desc       = request.form.get('description', '').strip()
        club_email = request.form.get('club_email', '').strip() or None
        coord_id   = request.form.get('coordinator_id') or None
        if coord_id:
            coord_id = int(coord_id)

        if not name:
            flash("Club name is required.", "danger")
        else:
            try:
                club_id = create_club(name, desc, coord_id, club_email)
                for img in request.files.getlist('club_images'):
                    if img and img.filename:
                        try:
                            path = save_upload(img, f"club_{club_id}")
                            add_club_image(club_id, path)
                        except ValueError as e:
                            flash(str(e), "warning")
                log_action(session['user_id'], 'CREATE_CLUB', 'club', club_id, name)
                flash("Club created successfully!", "success")
                return redirect(url_for('clubs.list_clubs'))
            except Exception as e:
                flash(f"Error creating club: {e}", "danger")

    users = get_all_users()
    user  = get_user_by_id(session['user_id'])
    return render_template('clubs/create.html', users=users, user=user, active='clubs')


# ── Edit ───────────────────────────────────────────────────────────────────────
@bp.route('/<int:club_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(club_id):
    if not _can_manage_club(club_id):
        flash("You can only manage your own club.", "danger")
        return redirect(url_for('dashboard.index'))

    club   = get_club_by_id(club_id)
    images = get_club_images(club_id)

    if request.method == 'POST':
        name       = request.form.get('club_name', '').strip()
        desc       = request.form.get('description', '').strip()
        club_email = request.form.get('club_email', '').strip() or None
        try:
            update_club(club_id, name, desc, club_email)
            for img in request.files.getlist('club_images'):
                if img and img.filename:
                    try:
                        path = save_upload(img, f"club_{club_id}")
                        add_club_image(club_id, path)
                    except ValueError as e:
                        flash(str(e), "warning")
            log_action(session['user_id'], 'UPDATE_CLUB', 'club', club_id, name)
            flash("Club updated!", "success")
            return redirect(url_for('clubs.detail', club_id=club_id))
        except Exception as e:
            flash(f"Error: {e}", "danger")

    user = get_user_by_id(session['user_id'])
    return render_template('clubs/edit.html',
                           club=club, club_images=images,
                           user=user, active='clubs')


# ── Delete ─────────────────────────────────────────────────────────────────────
@bp.route('/<int:club_id>/delete', methods=['POST'])
@admin_required
def delete(club_id):
    try:
        for img in get_club_images(club_id):
            delete_upload(img['img_path'])
        delete_club(club_id)
        log_action(session['user_id'], 'DELETE_CLUB', 'club', club_id)
        flash("Club deleted.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('clubs.list_clubs'))


# ── Delete image (AJAX) ────────────────────────────────────────────────────────
@bp.route('/<int:club_id>/delete_image/<int:img_id>', methods=['POST'])
@login_required
def delete_image(club_id, img_id):
    if not _can_manage_club(club_id):
        return jsonify({"success": False, "error": "Permission denied"})
    try:
        path = delete_club_image(img_id)
        if path:
            delete_upload(path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ── Image Download ─────────────────────────────────────────────────────────────
@bp.route('/<int:club_id>/images/<int:img_id>/download')
@login_required
def download_image(club_id, img_id):
    import os
    from flask import send_file, abort
    images = get_club_images(club_id)
    img = next((i for i in images if i['img_id'] == img_id), None)
    if not img:
        abort(404)
    path = os.path.join(os.getcwd(), 'static', img['img_path'])
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@bp.route('/<int:club_id>/gallery/zip')
@login_required
def download_gallery_zip(club_id):
    import os, io, zipfile
    from flask import send_file
    club   = get_club_by_id(club_id)
    images = get_club_images(club_id)
    if not images:
        flash("No images to download.", "warning")
        return redirect(url_for('clubs.detail', club_id=club_id))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            path = os.path.join(os.getcwd(), 'static', img['img_path'])
            if os.path.exists(path):
                zf.write(path, os.path.basename(path))
    buf.seek(0)
    safe_name = (club['club_name'] if club else f'club_{club_id}').replace(' ', '_')
    return send_file(buf, as_attachment=True,
                     download_name=f'{safe_name}_gallery.zip',
                     mimetype='application/zip')


# ── Members ────────────────────────────────────────────────────────────────────
@bp.route('/<int:club_id>/members')
@login_required
def members(club_id):
    club    = get_club_by_id(club_id)
    if not club:
        flash("Club not found.", "danger")
        return redirect(url_for('clubs.list_clubs'))

    members_list = get_club_members(club_id)
    non_members  = get_non_members(club_id) if _can_manage_club(club_id) else []
    user         = get_user_by_id(session['user_id'])

    return render_template('clubs/members.html',
                           club=club,
                           members=members_list,
                           non_members=non_members,
                           positions=POSITIONS,
                           can_manage=_can_manage_club(club_id),
                           user=user, active='clubs')


@bp.route('/<int:club_id>/members/add', methods=['POST'])
@login_required
def member_add(club_id):
    if not _can_manage_club(club_id):
        flash("Permission denied.", "danger")
        return redirect(url_for('clubs.members', club_id=club_id))
    user_id  = request.form.get('user_id', type=int)
    position = request.form.get('position', 'Member')
    try:
        add_member(club_id, user_id, position)
        log_action(session['user_id'], 'ADD_MEMBER', 'club', club_id, f"user_id={user_id}")
        flash("Member added.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('clubs.members', club_id=club_id))


@bp.route('/<int:club_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def member_remove(club_id, user_id):
    if not _can_manage_club(club_id):
        flash("Permission denied.", "danger")
        return redirect(url_for('clubs.members', club_id=club_id))
    try:
        remove_member(club_id, user_id)
        log_action(session['user_id'], 'REMOVE_MEMBER', 'club', club_id, f"user_id={user_id}")
        flash("Member removed.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('clubs.members', club_id=club_id))


@bp.route('/<int:club_id>/members/<int:user_id>/position', methods=['POST'])
@login_required
def member_position(club_id, user_id):
    if not _can_manage_club(club_id):
        flash("Permission denied.", "danger")
        return redirect(url_for('clubs.members', club_id=club_id))
    position = request.form.get('position', 'Member')
    try:
        change_position(club_id, user_id, position)
        flash("Position updated.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('clubs.members', club_id=club_id))


# ── Membership management (coordinator/admin only) ────────────────────────────

@bp.route('/<int:club_id>/requests')
@login_required
def membership_requests(club_id):
    if not _can_manage_club(club_id):
        flash("Permission denied.", "danger")
        return redirect(url_for('dashboard.index'))
    club     = get_club_by_id(club_id)
    requests = get_requests_for_club(club_id)
    user     = get_user_by_id(session['user_id'])
    return render_template('clubs/membership_requests.html',
                           club=club, requests=requests,
                           user=user, active='clubs')


@bp.route('/membership_requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_membership(request_id):
    try:
        approve_request(request_id, session['user_id'])
        flash("Membership approved!", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    referer = request.referrer or url_for('clubs.list_clubs')
    return redirect(referer)


@bp.route('/membership_requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_membership(request_id):
    try:
        reject_request(request_id, session['user_id'])
        flash("Membership rejected.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    referer = request.referrer or url_for('clubs.list_clubs')
    return redirect(referer)

