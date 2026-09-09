"""Campus Connect RBAC: messaging permissions and announcement targeting."""
import pytest
import services.connect_service as connect_service


def _mock_users(monkeypatch, users_by_id):
    monkeypatch.setattr(connect_service, '_get_users_brief', lambda ids: {
        uid: users_by_id[uid] for uid in ids if uid in users_by_id
    })


def test_admin_can_message_anyone(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'admin', 'club_id': None},
        2: {'user_id': 2, 'role': 'student', 'club_id': None},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 0)
    assert connect_service.can_message(1, 2) is True


def test_reply_always_allowed_once_conversation_exists(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'student', 'club_id': None},
        2: {'user_id': 2, 'role': 'student', 'club_id': None},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 3)
    assert connect_service.can_message(1, 2) is True


def test_student_can_initiate_to_coordinator(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'student', 'club_id': None},
        2: {'user_id': 2, 'role': 'club_admin', 'club_id': 3},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 0)
    assert connect_service.can_message(1, 2) is True


def test_student_cannot_initiate_to_random_student(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'student', 'club_id': None},
        2: {'user_id': 2, 'role': 'student', 'club_id': None},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 0)
    assert connect_service.can_message(1, 2) is False


def test_coordinator_can_initiate_to_own_club_member(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'club_admin', 'club_id': 3},
        2: {'user_id': 2, 'role': 'student', 'club_id': None},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 0)
    monkeypatch.setattr('services.member_service.is_member', lambda club_id, user_id: club_id == 3 and user_id == 2)
    assert connect_service.can_message(1, 2) is True


def test_coordinator_cannot_initiate_to_non_member_student(monkeypatch):
    _mock_users(monkeypatch, {
        1: {'user_id': 1, 'role': 'club_admin', 'club_id': 3},
        2: {'user_id': 2, 'role': 'student', 'club_id': None},
    })
    monkeypatch.setattr(connect_service, 'count_conversation', lambda a, b: 0)
    monkeypatch.setattr('services.member_service.is_member', lambda club_id, user_id: False)
    assert connect_service.can_message(1, 2) is False


def test_cannot_message_self():
    assert connect_service.can_message(1, 1) is False


# ── Announcement RBAC ──────────────────────────────────────────────────────

def test_student_cannot_create_announcement():
    with pytest.raises(PermissionError):
        connect_service.create_announcement(
            author_id=1, author_role='student', author_club_id=None,
            target_type='everyone', target_id=None, title='Hi', body='Body'
        )


def test_coordinator_cannot_broadcast_outside_own_club(monkeypatch):
    with pytest.raises(PermissionError):
        connect_service.create_announcement(
            author_id=1, author_role='club_admin', author_club_id=3,
            target_type='everyone', target_id=None, title='Hi', body='Body'
        )


def test_coordinator_cannot_target_other_club(monkeypatch):
    with pytest.raises(PermissionError):
        connect_service.create_announcement(
            author_id=1, author_role='club_admin', author_club_id=3,
            target_type='club', target_id=99, title='Hi', body='Body'
        )


def test_coordinator_can_broadcast_to_own_club(monkeypatch, fake_db):
    monkeypatch.setattr(connect_service, '_fanout_announcement_notifications', lambda *a, **k: None)
    ann_id = connect_service.create_announcement(
        author_id=1, author_role='club_admin', author_club_id=3,
        target_type='club', target_id=3, title='Hi', body='Body'
    )
    assert ann_id == 1  # FakeCursor.lastrowid default


def test_admin_can_broadcast_to_everyone(monkeypatch, fake_db):
    monkeypatch.setattr(connect_service, '_fanout_announcement_notifications', lambda *a, **k: None)
    ann_id = connect_service.create_announcement(
        author_id=1, author_role='admin', author_club_id=None,
        target_type='everyone', target_id=None, title='Hi', body='Body'
    )
    assert ann_id == 1
