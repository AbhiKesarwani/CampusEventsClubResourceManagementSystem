# routes/events.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required, club_admin_required, admin_required
from helpers.upload_helpers import save_upload, delete_upload
from services.user_service import get_user_by_id
from services.event_service import (
    get_all_events, get_event_by_id, get_event_images, get_event_resources,
    create_event, update_event, delete_event,
    add_event_image, delete_event_image, get_related_events
)
from services.club_service import get_clubs_for_select, get_club_by_id
from services.venue_service import get_venues_for_select
from services.resource_service import get_all_resources
from services.log_service import log_action
from services.recommendation_service import log_view

bp = Blueprint('events', __name__, url_prefix='/events')


@bp.route('/')
@login_required
def list_events():
    club_id   = request.args.get('club_id', type=int)
    venue_id  = request.args.get('venue_id', type=int)
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    upcoming  = bool(request.args.get('upcoming'))
    past      = bool(request.args.get('past'))

    # club_admin only sees their club's events
    role = session.get('role')
    if role == 'club_admin':
        club_id = session.get('club_id')

    events = get_all_events(club_id=club_id, venue_id=venue_id,
                            date_from=date_from, date_to=date_to,
                            upcoming=upcoming, past=past)

    clubs  = get_clubs_for_select()
    venues = get_venues_for_select()
    user   = get_user_by_id(session['user_id'])

    return render_template('events/list.html',
                           events=events,
                           clubs=clubs, venues=venues,
                           user=user, active='events',
                           filters={
                               'club_id': club_id, 'venue_id': venue_id,
                               'date_from': date_from, 'date_to': date_to,
                               'upcoming': upcoming, 'past': past
                           })


@bp.route('/<int:event_id>')
@login_required
def detail(event_id):
    event    = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    images    = get_event_images(event_id)
    resources = get_event_resources(event_id)
    user      = get_user_by_id(session['user_id'])
    related   = get_related_events(event_id, event['club_id'], limit=3)

    # Log the view for recommendation engine
    log_view(session['user_id'], event_id)

    return render_template('events/detail.html',
                           event=event, event_images=images,
                           event_resources=resources,
                           related_events=related,
                           user=user, active='events')


@bp.route('/create', methods=['GET', 'POST'])
@club_admin_required
def create():
    role    = session.get('role')
    clubs   = get_clubs_for_select() if role == 'admin' else []
    venues  = get_venues_for_select()
    resources_list = get_all_resources()

    # For club_admin, force their club
    default_club_id = None
    if role == 'club_admin':
        default_club_id = session.get('club_id')
        if default_club_id:
            clubs = [get_club_by_id(default_club_id)] if get_club_by_id(default_club_id) else []

    if request.method == 'POST':
        club_id   = request.form.get('club_id') if role == 'admin' else default_club_id
        title     = request.form.get('title', '').strip()
        desc      = request.form.get('description', '').strip()
        lead      = request.form.get('event_lead', '').strip()
        contact   = request.form.get('contact_no', '').strip()
        venue_id  = request.form.get('venue_id') or None
        date      = request.form.get('date')
        start_t   = request.form.get('start_time')
        end_t     = request.form.get('end_time')
        reg_link  = request.form.get('registration_link', '').strip()

        # club_admin guard
        if role == 'club_admin' and (not club_id or int(club_id) != int(default_club_id)):
            flash("You can only create events for your own club.", "danger")
            return redirect(url_for('events.list_events'))

        try:
            event_id = create_event(club_id, title, desc, lead, contact,
                                    venue_id, date, start_t, end_t,
                                    reg_link, session['user_id'])
            # Upload images
            for img in request.files.getlist('event_images'):
                if img and img.filename:
                    try:
                        path = save_upload(img, f"event_{event_id}")
                        add_event_image(event_id, path)
                    except ValueError as e:
                        flash(str(e), "warning")

            log_action(session['user_id'], 'CREATE_EVENT', 'event', event_id, title)
            flash("Event created successfully!", "success")
            return redirect(url_for('events.detail', event_id=event_id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Error creating event: {e}", "danger")

    user = get_user_by_id(session['user_id'])
    return render_template('events/create.html',
                           clubs=clubs, venues=venues,
                           resources=resources_list,
                           default_club_id=default_club_id,
                           user=user, active='events')


@bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@club_admin_required
def edit(event_id):
    event  = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    role = session.get('role')
    # club_admin can only edit their own club's events
    if role == 'club_admin' and event['club_id'] != session.get('club_id'):
        flash("You can only edit events belonging to your club.", "danger")
        return redirect(url_for('events.list_events'))

    if request.method == 'POST':
        club_id  = request.form.get('club_id') if role == 'admin' else event['club_id']
        title    = request.form.get('title', '').strip()
        desc     = request.form.get('description', '').strip()
        lead     = request.form.get('event_lead', '').strip()
        contact  = request.form.get('contact_no', '').strip()
        venue_id = request.form.get('venue_id') or None
        date     = request.form.get('date')
        start_t  = request.form.get('start_time')
        end_t    = request.form.get('end_time')
        reg_link = request.form.get('registration_link', '').strip()
        try:
            update_event(event_id, club_id, title, desc, lead, contact,
                         venue_id, date, start_t, end_t, reg_link)
            for img in request.files.getlist('event_images'):
                if img and img.filename:
                    try:
                        path = save_upload(img, f"event_{event_id}")
                        add_event_image(event_id, path)
                    except ValueError as e:
                        flash(str(e), "warning")
            log_action(session['user_id'], 'UPDATE_EVENT', 'event', event_id, title)
            flash("Event updated!", "success")
            return redirect(url_for('events.detail', event_id=event_id))
        except Exception as e:
            flash(f"Error: {e}", "danger")

    images = get_event_images(event_id)
    clubs  = get_clubs_for_select() if role == 'admin' else []
    venues = get_venues_for_select()
    user   = get_user_by_id(session['user_id'])
    return render_template('events/edit.html',
                           event=event, event_images=images,
                           clubs=clubs, venues=venues,
                           user=user, active='events')


@bp.route('/<int:event_id>/delete', methods=['POST'])
@club_admin_required
def delete(event_id):
    event = get_event_by_id(event_id)
    role  = session.get('role')
    if role == 'club_admin' and event and event['club_id'] != session.get('club_id'):
        flash("Access denied.", "danger")
        return redirect(url_for('events.list_events'))
    try:
        for img in get_event_images(event_id):
            delete_upload(img['img_path'])
        delete_event(event_id)
        log_action(session['user_id'], 'DELETE_EVENT', 'event', event_id)
        flash("Event deleted.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('events.list_events'))


@bp.route('/<int:event_id>/delete_image/<int:img_id>', methods=['POST'])
@club_admin_required
def delete_image(event_id, img_id):
    event = get_event_by_id(event_id)
    role  = session.get('role')
    if role == 'club_admin' and event and event['club_id'] != session.get('club_id'):
        flash("Access denied.", "danger")
        return redirect(url_for('events.edit', event_id=event_id))
    try:
        path = delete_event_image(img_id, event_id)
        if path:
            delete_upload(path)
        flash("Image deleted.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for('events.edit', event_id=event_id))


# ── Gallery Download ───────────────────────────────────────────────────────────

@bp.route('/<int:event_id>/image/<int:img_id>/download')
@login_required
def download_image(event_id, img_id):
    """Download a single event image."""
    import os
    from flask import send_file, abort
    images = get_event_images(event_id)
    img = next((i for i in images if i['img_id'] == img_id), None)
    if not img:
        abort(404)
    path = os.path.join(os.getcwd(), 'static', img['img_path'])
    if not os.path.exists(path):
        abort(404)
    filename = os.path.basename(path)
    return send_file(path, as_attachment=True, download_name=filename)


@bp.route('/<int:event_id>/gallery/zip')
@login_required
def download_gallery_zip(event_id):
    """Download all event images as a ZIP file."""
    import os
    import io
    import zipfile
    from flask import send_file
    event  = get_event_by_id(event_id)
    images = get_event_images(event_id)
    if not images:
        flash("No images to download.", "warning")
        return redirect(url_for('events.detail', event_id=event_id))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            path = os.path.join(os.getcwd(), 'static', img['img_path'])
            if os.path.exists(path):
                zf.write(path, os.path.basename(path))
    buf.seek(0)
    safe_name = (event['title'] if event else f"event_{event_id}").replace(' ', '_')
    return send_file(buf, as_attachment=True,
                     download_name=f"{safe_name}_gallery.zip",
                     mimetype='application/zip')

