# routes/notifications.py
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.notification_service import (
    get_user_notifications, mark_read, mark_all_read,
    delete_notification, delete_all_notifications
)

bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@bp.route('/')
@login_required
def index():
    user_id = session['user_id']
    notifs  = get_user_notifications(user_id)
    user    = get_user_by_id(user_id)
    return render_template('notifications.html',
                           notifications=notifs, user=user,
                           active='notifications')


@bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_one_read(notif_id):
    mark_read(notif_id, session['user_id'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('notifications.index'))


@bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all():
    mark_all_read(session['user_id'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    flash("All notifications marked as read.", "success")
    return redirect(url_for('notifications.index'))


@bp.route('/<int:notif_id>/delete', methods=['POST'])
@login_required
def delete_one(notif_id):
    deleted = delete_notification(notif_id, session['user_id'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': deleted})
    if deleted:
        flash("Notification deleted.", "success")
    return redirect(url_for('notifications.index'))


@bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all():
    delete_all_notifications(session['user_id'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    flash("All notifications cleared.", "success")
    return redirect(url_for('notifications.index'))
