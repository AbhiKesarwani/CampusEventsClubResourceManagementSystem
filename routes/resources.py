# routes/resources.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required, admin_required, club_admin_required
from services.user_service import get_user_by_id
from services.resource_service import (
    get_all_resources, get_resource_by_id,
    create_resource, update_resource, delete_resource,
    get_all_requests, get_requests_for_club,
    create_request, approve_request, reject_request
)
from services.event_service import get_events_for_club, get_all_events
from services.club_service import get_clubs_for_select
from services.log_service import log_action

bp = Blueprint('resources', __name__, url_prefix='/resources')


@bp.route('/')
@login_required
def list_resources():
    resources = get_all_resources()
    user      = get_user_by_id(session['user_id'])
    return render_template('resources/list.html',
                           resources=resources, user=user, active='resources')


@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    if request.method == 'POST':
        name     = request.form.get('resource_name', '').strip()
        qty      = request.form.get('total_quantity', 0)
        desc     = request.form.get('description', '').strip()
        if not name:
            flash("Resource name required.", "danger")
        else:
            try:
                rid = create_resource(name, int(qty), desc)
                log_action(session['user_id'], 'CREATE_RESOURCE', 'resource', rid, name)
                flash("Resource created!", "success")
                return redirect(url_for('resources.list_resources'))
            except Exception as e:
                flash(f"Error: {e}", "danger")
    user = get_user_by_id(session['user_id'])
    return render_template('resources/create.html', user=user, active='resources')


@bp.route('/<int:resource_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(resource_id):
    resource = get_resource_by_id(resource_id)
    if not resource:
        flash("Resource not found.", "danger")
        return redirect(url_for('resources.list_resources'))

    if request.method == 'POST':
        name = request.form.get('resource_name', '').strip()
        qty  = request.form.get('total_quantity', 0)
        desc = request.form.get('description', '').strip()
        try:
            update_resource(resource_id, name, int(qty), desc)
            log_action(session['user_id'], 'UPDATE_RESOURCE', 'resource', resource_id, name)
            flash("Resource updated!", "success")
            return redirect(url_for('resources.list_resources'))
        except Exception as e:
            flash(f"Error: {e}", "danger")

    user = get_user_by_id(session['user_id'])
    return render_template('resources/edit.html',
                           resource=resource, user=user, active='resources')


@bp.route('/<int:resource_id>/delete', methods=['POST'])
@admin_required
def delete(resource_id):
    try:
        delete_resource(resource_id)
        log_action(session['user_id'], 'DELETE_RESOURCE', 'resource', resource_id)
        flash("Resource deleted.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('resources.list_resources'))


# ── Resource Request Workflow ─────────────────────────────────────────────────

@bp.route('/requests')
@admin_required
def all_requests():
    status   = request.args.get('status')
    requests = get_all_requests(status if status else None)
    user     = get_user_by_id(session['user_id'])
    return render_template('resources/requests.html',
                           requests=requests, status_filter=status,
                           user=user, active='resources')


@bp.route('/request', methods=['GET', 'POST'])
@club_admin_required
def submit_request():
    club_id = session.get('club_id')
    role    = session.get('role')

    if role == 'admin':
        events    = get_all_events()
        clubs     = get_clubs_for_select()
    else:
        events    = get_events_for_club(club_id)
        clubs     = []

    resources = get_all_resources()

    if request.method == 'POST':
        event_id    = request.form.get('event_id', type=int)
        resource_id = request.form.get('resource_id', type=int)
        quantity    = request.form.get('quantity', type=int, default=1)
        reason      = request.form.get('reason', '').strip() or None

        req_club_id = club_id
        if role == 'admin':
            req_club_id = request.form.get('club_id', type=int)

        try:
            rid = create_request(event_id, req_club_id, resource_id, quantity, session['user_id'], reason)
            log_action(session['user_id'], 'REQUEST_RESOURCE', 'resource_request', rid)
            flash("Resource request submitted!", "success")
            return redirect(url_for('resources.my_requests'))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Error: {e}", "danger")

    user = get_user_by_id(session['user_id'])
    return render_template('resources/request.html',
                           events=events, resources=resources, clubs=clubs,
                           user=user, active='resources')


@bp.route('/requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve(request_id):
    try:
        approve_request(request_id, session['user_id'])
        log_action(session['user_id'], 'APPROVE_RESOURCE_REQUEST', 'resource_request', request_id)
        flash("Request approved and resources allocated!", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('resources.all_requests'))


@bp.route('/requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject(request_id):
    try:
        reject_request(request_id, session['user_id'])
        log_action(session['user_id'], 'REJECT_RESOURCE_REQUEST', 'resource_request', request_id)
        flash("Request rejected.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('resources.all_requests'))


@bp.route('/my-requests')
@login_required
def my_requests():
    """Club coordinator views their club's resource requests."""
    role    = session.get('role')
    club_id = session.get('club_id')

    if role == 'admin':
        return redirect(url_for('resources.all_requests'))
    if role != 'club_admin' or not club_id:
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard.index'))

    reqs = get_requests_for_club(club_id)
    user = get_user_by_id(session['user_id'])
    return render_template('resources/my_requests.html',
                           requests=reqs, user=user, active='resource_requests')
