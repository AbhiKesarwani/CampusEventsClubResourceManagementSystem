# routes/notifications.py
from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from helpers.auth_helpers import login_required
from services.notification_service import (
    get_user_notifications, mark_read, mark_all_read
)
from services.user_service import get_user_by_id

bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@bp.route('/')
@login_required
def index():
    user  = get_user_by_id(session['user_id'])
    notifs = get_user_notifications(session['user_id'])
    return render_template('notifications.html',
                           notifications=notifs,
                           user=user, active='notifications')


@bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def read_one(notif_id):
    mark_read(notif_id, session['user_id'])
    if request.is_json:
        return jsonify({'success': True})
    return redirect(url_for('notifications.index'))


@bp.route('/read_all', methods=['POST'])
@login_required
def read_all():
    mark_all_read(session['user_id'])
    return redirect(url_for('notifications.index'))
