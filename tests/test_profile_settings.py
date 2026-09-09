"""Profile & Settings pages: rendering, own-profile editing, and RBAC on
viewing other users' profiles."""
from tests.conftest import login_as

_REAL_USER = {'user_id': 1, 'name': 'Test Student', 'email': 't@example.com',
             'role': 'student', 'club_id': None, 'avatar_path': None, 'phone': None}


def test_own_profile_renders(client, monkeypatch):
    import routes.profile as profile_routes
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: _REAL_USER)
    login_as(client, role='student', user_id=1)
    resp = client.get('/profile/')
    assert resp.status_code == 200


def test_settings_page_renders(client, monkeypatch):
    import routes.settings as settings_routes
    monkeypatch.setattr(settings_routes, 'get_user_by_id', lambda uid: _REAL_USER)
    login_as(client, role='student')
    resp = client.get('/settings/')
    assert resp.status_code == 200


def test_student_cannot_view_other_students_profile(client, monkeypatch):
    import routes.profile as profile_routes
    monkeypatch.setattr(profile_routes, 'get_user_by_id',
                        lambda uid: {'user_id': uid, 'name': 'Someone', 'role': 'student'})
    login_as(client, role='student', user_id=1)
    resp = client.get('/profile/2', follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/profile/'  # bounced back to own profile


def test_admin_can_view_any_profile(client, monkeypatch):
    import routes.profile as profile_routes
    monkeypatch.setattr(profile_routes, 'get_user_by_id',
                        lambda uid: {'user_id': uid, 'name': 'Someone', 'role': 'student', 'club_id': None})
    login_as(client, role='admin', user_id=1)
    resp = client.get('/profile/2')
    assert resp.status_code == 200


def test_change_password_wrong_current_rejected(client, monkeypatch):
    import routes.profile as profile_routes
    from werkzeug.security import generate_password_hash
    real_user = {'user_id': 1, 'name': 'Test', 'password_hash': generate_password_hash('correct-pw', method='pbkdf2:sha256')}
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: real_user)

    called = {'update': False}
    monkeypatch.setattr(profile_routes, 'update_password', lambda *a, **k: called.update(update=True))

    login_as(client, role='student', user_id=1)
    resp = client.post('/profile/change-password', data={
        'current_password': 'wrong-pw', 'new_password': 'newpass123', 'confirm_password': 'newpass123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert called['update'] is False


def test_change_password_mismatch_rejected(client, monkeypatch):
    import routes.profile as profile_routes
    from werkzeug.security import generate_password_hash
    real_user = {'user_id': 1, 'name': 'Test', 'password_hash': generate_password_hash('correct-pw', method='pbkdf2:sha256')}
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: real_user)

    called = {'update': False}
    monkeypatch.setattr(profile_routes, 'update_password', lambda *a, **k: called.update(update=True))

    login_as(client, role='student', user_id=1)
    resp = client.post('/profile/change-password', data={
        'current_password': 'correct-pw', 'new_password': 'newpass123', 'confirm_password': 'DIFFERENT'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert called['update'] is False


def test_change_password_success(client, monkeypatch):
    import routes.profile as profile_routes
    from werkzeug.security import generate_password_hash
    real_user = {'user_id': 1, 'name': 'Test', 'password_hash': generate_password_hash('correct-pw', method='pbkdf2:sha256')}
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: real_user)

    called = {'update': False}
    monkeypatch.setattr(profile_routes, 'update_password', lambda *a, **k: called.update(update=True))

    login_as(client, role='student', user_id=1)
    resp = client.post('/profile/change-password', data={
        'current_password': 'correct-pw', 'new_password': 'newpass123', 'confirm_password': 'newpass123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert called['update'] is True


def test_settings_preferences_save(client):
    login_as(client, role='student')
    resp = client.post('/settings/preferences', data={
        'notifications_enabled': 'on', 'ai_response_style': 'detailed', 'profile_visibility': 'private'
    }, follow_redirects=True)
    assert resp.status_code == 200
