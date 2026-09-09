"""Campus Connect routes: page rendering, AI ask/escalate, messaging RBAC,
announcements, and admin moderation — at the HTTP layer."""
from tests.conftest import login_as


def test_connect_page_renders_for_every_role(client):
    for role, club_id in [('student', None), ('club_admin', 3), ('admin', None)]:
        login_as(client, role=role, club_id=club_id)
        resp = client.get('/connect/')
        assert resp.status_code == 200, f"failed for role={role}"


def test_ai_ask_requires_question(client):
    login_as(client, role='student')
    resp = client.post('/connect/api/ai/ask', json={'question': ''})
    assert resp.status_code == 400


def test_ai_ask_returns_json_shape(client):
    login_as(client, role='student')
    resp = client.post('/connect/api/ai/ask', json={'question': 'When is the next event?'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(['answer', 'source', 'intent', 'escalate', 'confidence']).issubset(data.keys())


def test_send_message_blocked_by_rbac(client, monkeypatch):
    import services.connect_service as connect_service
    monkeypatch.setattr(connect_service, 'can_message', lambda sender, receiver: False)
    login_as(client, role='student', user_id=1)
    resp = client.post('/connect/api/conversations/999/send', json={'body': 'hi'})
    assert resp.status_code == 403


def test_send_message_allowed_by_rbac(client, monkeypatch):
    import services.connect_service as connect_service
    monkeypatch.setattr(connect_service, 'can_message', lambda sender, receiver: True)
    login_as(client, role='student', user_id=1)
    resp = client.post('/connect/api/conversations/2/send', json={'body': 'hi coordinator'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_student_cannot_create_announcement_via_route(client):
    login_as(client, role='student')
    resp = client.post('/connect/announcements/create', json={
        'target_type': 'everyone', 'title': 'Hack', 'body': 'nope'
    })
    assert resp.status_code == 403


def test_admin_can_create_announcement_via_route(client, monkeypatch):
    import services.connect_service as connect_service
    monkeypatch.setattr(connect_service, '_fanout_announcement_notifications', lambda *a, **k: None)
    login_as(client, role='admin')
    resp = client.post('/connect/announcements/create', json={
        'target_type': 'everyone', 'title': 'Welcome', 'body': 'Hello campus'
    })
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_admin_moderation_conversations_requires_admin(client):
    login_as(client, role='student')
    resp = client.get('/connect/api/admin/conversations', follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/'  # bounced away from admin-only endpoint


def test_unread_count_endpoint(client):
    login_as(client, role='student')
    resp = client.get('/connect/api/unread-count')
    assert resp.status_code == 200
    assert 'unread' in resp.get_json()
