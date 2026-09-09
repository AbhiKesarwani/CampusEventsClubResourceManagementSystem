# routes/connect.py
# Campus Connect — unified messaging, announcements & AI assistant blueprint.
# Reuses: helpers.auth_helpers (RBAC), services.user_service, services.club_service,
#         services.notification_service (via connect_service), services.connect_service,
#         services.ai_service.
from flask import Blueprint, render_template, request, session, jsonify
from helpers.auth_helpers import login_required, admin_required
from services.user_service import get_user_by_id
from services.club_service import get_clubs_for_select
import services.connect_service as connect_service
import services.ai_service as ai_service

bp = Blueprint('connect', __name__, url_prefix='/connect')


def _current_user() -> dict:
    return {
        'user_id': session['user_id'],
        'name':    session.get('name'),
        'role':    session.get('role', 'student'),
        'club_id': session.get('club_id'),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/')
@login_required
def index():
    me   = _current_user()
    user = get_user_by_id(me['user_id'])

    inbox         = connect_service.get_inbox(me['user_id'])
    unread_msgs   = connect_service.count_unread_messages(me['user_id'])
    ai_history    = connect_service.get_ai_history(me['user_id'], limit=30)
    announcements = connect_service.get_announcements_for_user(me['user_id'], me['role'], me['club_id'])
    contacts      = connect_service.search_contacts('', me['user_id'], me['role'], me['club_id'])

    clubs_for_select = get_clubs_for_select() if me['role'] == 'admin' else []

    return render_template(
        'connect/index.html',
        user=user,
        active='connect',
        role=me['role'],
        club_id=me['club_id'],
        inbox=inbox,
        unread_messages=unread_msgs,
        ai_history=ai_history,
        announcements=announcements,
        contacts=contacts,
        clubs_for_select=clubs_for_select,
        initial_tab=request.args.get('tab', 'ai'),
        initial_with=request.args.get('with', type=int),
        initial_ann=request.args.get('ann', type=int),
    )


# ═══════════════════════════════════════════════════════════════════════════
# AI ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/ai/ask', methods=['POST'])
@login_required
def ai_ask():
    me = _current_user()
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'error': 'Question is required.'}), 400
    if len(question) > 1000:
        question = question[:1000]

    history_rows = connect_service.get_ai_history(me['user_id'], limit=12)
    history = [{'role': h['role'], 'content': h['content']} for h in history_rows]

    from services.user_service import get_preferences
    style = get_preferences(me['user_id']).get('ai_response_style', 'concise')

    result = ai_service.campus_connect_ai(question, me['user_id'], history=history, response_style=style)

    # Only persist to history when the AI actually produced a real response.
    # source='error' means the AI was rate-limited or otherwise unavailable —
    # saving that to the conversation log would corrupt future context.
    if result.get('source') != 'error':
        connect_service.save_ai_message(me['user_id'], 'user', question, source='user')
        connect_service.save_ai_message(me['user_id'], 'assistant', result['answer'],
                                        source=result['source'])

    return jsonify(result)


@bp.route('/api/ai/escalate', methods=['POST'])
@login_required
def ai_escalate():
    me = _current_user()
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    coordinator_id = data.get('coordinator_id')
    try:
        coordinator_id = int(coordinator_id) if coordinator_id else None
    except (TypeError, ValueError):
        coordinator_id = None

    if not question:
        return jsonify({'error': 'Question is required.'}), 400

    ok = connect_service.escalate_to_coordinator(
        me['user_id'], me['name'], question,
        coordinator_id=coordinator_id, club_id=me['club_id']
    )
    if not ok:
        return jsonify({'success': False, 'error': 'No coordinator is available right now.'}), 404
    return jsonify({'success': True})


@bp.route('/api/ai/history/clear', methods=['POST'])
@login_required
def ai_clear_history():
    connect_service.clear_ai_history(session['user_id'])
    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════════════════════════
# MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/contacts')
@login_required
def api_contacts():
    me = _current_user()
    q  = request.args.get('q', '')
    return jsonify(connect_service.search_contacts(q, me['user_id'], me['role'], me['club_id']))


@bp.route('/api/conversations')
@login_required
def api_conversations():
    me = _current_user()
    include_archived = request.args.get('archived') == '1'
    return jsonify(connect_service.get_inbox(me['user_id'], include_archived=include_archived))


@bp.route('/api/conversations/<int:other_id>')
@login_required
def api_conversation_thread(other_id):
    me = _current_user()
    other = get_user_by_id(other_id)
    if not other:
        return jsonify({'error': 'User not found.'}), 404

    has_history = connect_service.count_conversation(me['user_id'], other_id) > 0
    if not has_history and not connect_service.can_message(me['user_id'], other_id):
        return jsonify({'error': 'You are not allowed to message this user.'}), 403

    page = request.args.get('page', 1, type=int)
    messages = connect_service.get_conversation(me['user_id'], other_id, page=page, per_page=50)
    connect_service.mark_messages_read(me['user_id'], other_id)

    return jsonify({
        'other': {'user_id': other['user_id'], 'name': other['name'], 'role': other['role']},
        'messages': messages,
    })


@bp.route('/api/conversations/<int:other_id>/send', methods=['POST'])
@login_required
def api_conversation_send(other_id):
    me = _current_user()
    data = request.get_json(silent=True) or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'Message cannot be empty.'}), 400
    try:
        msg_id = connect_service.send_message(me['user_id'], other_id, body, sender_name=me['name'])
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'success': True, 'msg_id': msg_id})


@bp.route('/api/conversations/<int:other_id>/archive', methods=['POST'])
@login_required
def api_conversation_archive(other_id):
    data = request.get_json(silent=True) or {}
    archived = bool(data.get('archived', True))
    connect_service.set_conversation_archived(session['user_id'], other_id, archived)
    return jsonify({'success': True})


@bp.route('/api/conversations/<int:other_id>/delete', methods=['POST'])
@login_required
def api_conversation_delete(other_id):
    connect_service.delete_conversation(session['user_id'], other_id)
    return jsonify({'success': True})


@bp.route('/api/unread-count')
@login_required
def api_unread_count():
    return jsonify({'unread': connect_service.count_unread_messages(session['user_id'])})


# ── Admin moderation ────────────────────────────────────────────────────────

@bp.route('/api/admin/conversations')
@admin_required
def api_admin_conversations():
    search = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    return jsonify(connect_service.get_all_conversations_admin(search=search, page=page))


@bp.route('/api/admin/conversations/<int:user_a>/<int:user_b>')
@admin_required
def api_admin_conversation_thread(user_a, user_b):
    page = request.args.get('page', 1, type=int)
    messages = connect_service.get_conversation(user_a, user_b, page=page, per_page=50)
    ua, ub = get_user_by_id(user_a), get_user_by_id(user_b)
    return jsonify({
        'user_a': {'user_id': user_a, 'name': ua['name'] if ua else '?'},
        'user_b': {'user_id': user_b, 'name': ub['name'] if ub else '?'},
        'messages': messages,
    })


# ═══════════════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/announcements')
@login_required
def api_announcements():
    me = _current_user()
    page = request.args.get('page', 1, type=int)
    items = connect_service.get_announcements_for_user(me['user_id'], me['role'], me['club_id'], page=page)
    total = connect_service.count_announcements_for_user(me['user_id'], me['role'], me['club_id'])
    return jsonify({'items': items, 'total': total, 'page': page})


@bp.route('/announcements/create', methods=['POST'])
@login_required
def announcements_create():
    me = _current_user()
    data = request.get_json(silent=True) or {}
    target_type = (data.get('target_type') or '').strip()
    target_id   = data.get('target_id')
    title       = (data.get('title') or '').strip()
    body        = (data.get('body') or '').strip()
    pinned      = bool(data.get('pinned'))

    try:
        target_id = int(target_id) if target_id not in (None, '', 'null') else None
    except (TypeError, ValueError):
        target_id = None

    try:
        ann_id = connect_service.create_announcement(
            me['user_id'], me['role'], me['club_id'],
            target_type, target_id, title, body, pinned=pinned
        )
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'success': True, 'ann_id': ann_id})


@bp.route('/api/announcements/<int:ann_id>/pin', methods=['POST'])
@login_required
def api_announcement_pin(ann_id):
    me = _current_user()
    try:
        connect_service.toggle_pin_announcement(ann_id, me['user_id'], me['role'])
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    return jsonify({'success': True})


@bp.route('/api/announcements/<int:ann_id>/delete', methods=['POST'])
@login_required
def api_announcement_delete(ann_id):
    me = _current_user()
    try:
        connect_service.delete_announcement(ann_id, me['user_id'], me['role'])
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    return jsonify({'success': True})
