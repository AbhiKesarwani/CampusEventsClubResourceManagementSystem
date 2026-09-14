from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from helpers.auth_helpers import login_required, club_admin_required, admin_required
from helpers.upload_helpers import save_upload, delete_upload, get_image_path, build_gallery_zip
from services.user_service import get_user_by_id
from services.event_service import (
    get_all_events, count_all_events, get_event_by_id, get_event_images,
    create_event, update_event, delete_event,
    add_event_image, delete_event_image, get_related_events
)
from services.club_service import get_clubs_for_select, get_club_by_id
from services.venue_service import get_venues_for_select
from services.log_service import log_action
from services.recommendation_service import log_view
from services.attendance_service import has_attended
from services.certificate_service import certificate_exists
from helpers.pagination import paginate

bp = Blueprint('events', __name__, url_prefix='/events')

PER_PAGE = 12


@bp.route('/')
@login_required
def list_events():
    search  = request.args.get('search', '').strip()
    status  = request.args.get('status', '').lower().strip()   # '', 'upcoming', 'ongoing', 'past'
    page    = request.args.get('page', 1, type=int)
    club_id = request.args.get('club_id', type=int)  # kept for admin club filter

    # Count total for pagination
    total = count_all_events(club_id=club_id, search=search or None, status=status or None)
    page, total_pages, _ = paginate(total, page, PER_PAGE)

    # All roles see all events
    events = get_all_events(club_id=club_id, search=search or None, status=status or None,
                            page=page, per_page=PER_PAGE)

    clubs = get_clubs_for_select()  # used in admin club filter
    user  = get_user_by_id(session['user_id'])

    return render_template('events/list.html',
                           events=events,
                           clubs=clubs,
                           user=user, active='events',
                           page=page, total_pages=total_pages, total=total,
                           filters={
                               'search': search,
                               'status': status,
                               'club_id': club_id,
                           })



@bp.route('/my')
@login_required
def my_events():
    """Coordinator only: shows events for their own club."""
    role    = session.get('role')
    club_id = session.get('club_id')

    if role not in ('club_admin', 'admin'):
        flash("My Events is for club coordinators only.", "info")
        return redirect(url_for('events.list_events'))

    # Admin can filter by any club
    if role == 'admin':
        club_id = request.args.get('club_id', type=int) or club_id

    events = get_all_events(club_id=club_id)
    clubs  = get_clubs_for_select() if role == 'admin' else []
    venues = get_venues_for_select()
    user   = get_user_by_id(session['user_id'])

    return render_template('events/list.html',
                           events=events,
                           clubs=clubs, venues=venues,
                           user=user, active='my_events',
                           my_events_view=True,
                           filters={
                               'club_id': club_id, 'venue_id': None,
                               'date_from': None, 'date_to': None,
                               'upcoming': False, 'past': False
                           })


@bp.route('/<int:event_id>')
@login_required
def detail(event_id):
    event    = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    images    = get_event_images(event_id)
    user      = get_user_by_id(session['user_id'])
    related   = get_related_events(event_id, event['club_id'], limit=3)

    # Log the view for recommendation engine
    log_view(session['user_id'], event_id)

    timeline = _build_event_timeline(event, session['user_id'])

    return render_template('events/detail.html',
                           event=event, event_images=images,
                           related_events=related,
                           timeline=timeline,
                           user=user, active='events')


def _build_event_timeline(event: dict, user_id: int) -> list[dict]:
    """Derive the visual Registration -> Certificate pipeline stage-by-stage
    from existing event/attendance/certificate data (no new schema needed)."""
    from datetime import date, timedelta

    today = date.today()
    event_date = event.get('date')
    is_approved = event.get('approved_status') == 'Approved'
    is_past = bool(event_date and event_date < today)
    is_today = bool(event_date and event_date == today)
    is_soon = bool(event_date and today <= event_date <= today + timedelta(days=2))
    attended = has_attended(event['event_id'], user_id)
    has_cert = bool(certificate_exists(event['event_id'], user_id))

    return [
        {'label': 'Registration', 'icon': 'clipboard-check', 'done': True},
        {'label': 'Confirmation', 'icon': 'badge-check', 'done': is_approved},
        {'label': 'Reminder', 'icon': 'bell-ring', 'done': is_approved and (is_soon or is_today or is_past)},
        {'label': 'Event Starts', 'icon': 'play-circle', 'done': is_approved and (is_today or is_past)},
        {'label': 'Attendance', 'icon': 'check-circle', 'done': attended},
        {'label': 'Certificate Generated', 'icon': 'award', 'done': has_cert},
    ]


@bp.route('/create', methods=['GET', 'POST'])
@club_admin_required
def create():
    role    = session.get('role')
    clubs   = get_clubs_for_select() if role == 'admin' else []
    venues  = get_venues_for_select()

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
@login_required
def delete_image(event_id, img_id):
    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    role = session.get('role')
    # Only Admin or the event's Club Coordinator can delete photos
    if role != 'admin' and (role != 'club_admin' or event['club_id'] != session.get('club_id')):
        flash("Access denied. Only authorized coordinators or admins can delete photos.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    try:
        path = delete_event_image(img_id, event_id)
        if path:
            delete_upload(path)
        log_action(session['user_id'], 'DELETE_EVENT_PHOTO', 'event', event_id, f"Photo #{img_id}")
        flash("Photo deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting photo: {e}", "danger")

    # If redirected from edit page, return to edit; otherwise detail
    referer = request.headers.get('Referer', '')
    if '/edit' in referer:
        return redirect(url_for('events.edit', event_id=event_id))
    return redirect(url_for('events.detail', event_id=event_id))


# ── Event Photos Upload & Gallery ─────────────────────────────────────────────

@bp.route('/<int:event_id>/photos/upload', methods=['POST'])
@bp.route('/<int:event_id>/upload_photos', methods=['POST'])
@login_required
def upload_photos(event_id):
    """Upload one or more photos to an event's gallery (Admin or assigned Coordinator only)."""
    from werkzeug.utils import secure_filename
    event = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    role = session.get('role')
    if role != 'admin' and (role != 'club_admin' or event['club_id'] != session.get('club_id')):
        flash("Access denied. Only authorized coordinators or admins can upload event photos.", "danger")
        return redirect(url_for('events.detail', event_id=event_id))

    files = request.files.getlist('photos') or request.files.getlist('event_images')
    if not files or all(not f or not f.filename for f in files):
        flash("No photo files selected for upload.", "warning")
        return redirect(url_for('events.detail', event_id=event_id))

    uploaded_count = 0
    errors = []
    for f in files:
        if not f or not f.filename:
            continue
        try:
            original_name = secure_filename(f.filename)
            saved_path = save_upload(f, f"event_{event_id}")
            add_event_image(event_id, saved_path, uploaded_by=session['user_id'], original_filename=original_name)
            uploaded_count += 1
        except ValueError as e:
            errors.append(f"{f.filename}: {str(e)}")
        except Exception as e:
            errors.append(f"{f.filename}: Upload failed ({str(e)})")

    if uploaded_count > 0:
        log_action(session['user_id'], 'UPLOAD_EVENT_PHOTOS', 'event', event_id, f"Uploaded {uploaded_count} photos")
        flash(f"Successfully uploaded {uploaded_count} event photo{'s' if uploaded_count != 1 else ''}!", "success")
    if errors:
        for err in errors[:3]:  # show up to 3 errors
            flash(err, "warning")

    return redirect(url_for('events.detail', event_id=event_id))


# ── Gallery Download ───────────────────────────────────────────────────────────

@bp.route('/<int:event_id>/image/<int:img_id>/download')
@bp.route('/<int:event_id>/photos/<int:img_id>/download')
@login_required
def download_image(event_id, img_id):
    """Download a single event image."""
    import os
    from flask import send_file
    images = get_event_images(event_id)
    path = get_image_path(images, img_id)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@bp.route('/<int:event_id>/gallery/zip')
@bp.route('/<int:event_id>/photos/download')
@login_required
def download_gallery_zip(event_id):
    """Download all event photos as a secure ZIP file."""
    import re
    from flask import send_file
    event  = get_event_by_id(event_id)
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events.list_events'))

    images = get_event_images(event_id)
    if not images:
        flash("No photos available to download for this event.", "warning")
        return redirect(url_for('events.detail', event_id=event_id))

    buf = build_gallery_zip(images)
    clean_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', event.get('title', f"event_{event_id}"))[:40]
    zip_name = f"{clean_title}_event_{event_id}_photos.zip"

    return send_file(buf, as_attachment=True,
                     download_name=zip_name,
                     mimetype='application/zip')

