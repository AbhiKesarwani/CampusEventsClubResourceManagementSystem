# routes/venues.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required, admin_required
from services.user_service import get_user_by_id
from services.venue_service import (
    get_all_venues, get_venue_by_id,
    create_venue, update_venue, delete_venue
)
from services.log_service import log_action

bp = Blueprint('venues', __name__, url_prefix='/venues')


@bp.route('/')
@login_required
def list_venues():
    venues = get_all_venues()
    user   = get_user_by_id(session['user_id'])
    return render_template('venues/list.html', venues=venues, user=user, active='venues')


@bp.route('/<int:venue_id>')
@login_required
def detail(venue_id):
    venue = get_venue_by_id(venue_id)
    if not venue:
        flash("Venue not found.", "danger")
        return redirect(url_for('venues.list_venues'))
    user = get_user_by_id(session['user_id'])
    return render_template('venues/detail.html', venue=venue, user=user, active='venues')


@bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create():
    if request.method == 'POST':
        name     = request.form.get('venue_name', '').strip()
        capacity = request.form.get('capacity') or None
        location = request.form.get('location', '').strip()
        type_    = request.form.get('type', '').strip()
        if not name:
            flash("Venue name is required.", "danger")
        else:
            try:
                vid = create_venue(name, capacity, location, type_)
                log_action(session['user_id'], 'CREATE_VENUE', 'venue', vid, name)
                flash("Venue created!", "success")
                return redirect(url_for('venues.list_venues'))
            except Exception as e:
                flash(f"Error: {e}", "danger")
    user = get_user_by_id(session['user_id'])
    return render_template('venues/create.html', user=user, active='venues')


@bp.route('/<int:venue_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(venue_id):
    venue = get_venue_by_id(venue_id)
    if not venue:
        flash("Venue not found.", "danger")
        return redirect(url_for('venues.list_venues'))

    if request.method == 'POST':
        name     = request.form.get('venue_name', '').strip()
        capacity = request.form.get('capacity') or None
        location = request.form.get('location', '').strip()
        type_    = request.form.get('type', '').strip()
        try:
            update_venue(venue_id, name, capacity, location, type_)
            log_action(session['user_id'], 'UPDATE_VENUE', 'venue', venue_id, name)
            flash("Venue updated!", "success")
            return redirect(url_for('venues.detail', venue_id=venue_id))
        except Exception as e:
            flash(f"Error: {e}", "danger")

    user = get_user_by_id(session['user_id'])
    return render_template('venues/edit.html', venue=venue, user=user, active='venues')


@bp.route('/<int:venue_id>/delete', methods=['POST'])
@admin_required
def delete(venue_id):
    try:
        delete_venue(venue_id)
        log_action(session['user_id'], 'DELETE_VENUE', 'venue', venue_id)
        flash("Venue deleted.", "success")
    except Exception as e:
        flash(f"Error deleting venue (events may be linked): {e}", "danger")
    return redirect(url_for('venues.list_venues'))
