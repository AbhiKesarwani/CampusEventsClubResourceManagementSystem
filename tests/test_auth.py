"""Authentication: login, register, and role-based access control."""
from werkzeug.security import generate_password_hash
import pytest


FAKE_USER = {
    'user_id': 1, 'name': 'Asha Menon', 'email': 'asha@cecrms.com',
    'password_hash': generate_password_hash('student123', method='pbkdf2:sha256'),
    'role': 'student', 'phone': '9000000004', 'club_id': None,
}


def test_login_page_renders(client):
    resp = client.get('/login')
    assert resp.status_code == 200


def test_login_success_sets_session(client, monkeypatch):
    import routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, 'get_user_by_email', lambda email: FAKE_USER)

    resp = client.post('/login', data={'email': 'asha@cecrms.com', 'password': 'student123'},
                       follow_redirects=False)
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess['user_id'] == 1
        assert sess['role'] == 'student'


def test_login_wrong_password_flashes_and_stays(client, monkeypatch):
    import routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, 'get_user_by_email', lambda email: FAKE_USER)

    resp = client.post('/login', data={'email': 'asha@cecrms.com', 'password': 'wrong'},
                       follow_redirects=True)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_login_unknown_email(client, monkeypatch):
    import routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, 'get_user_by_email', lambda email: None)

    resp = client.post('/login', data={'email': 'nobody@example.com', 'password': 'x'},
                       follow_redirects=True)
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_register_requires_fields(client):
    resp = client.post('/register', data={'name': '', 'email': '', 'password': ''},
                       follow_redirects=True)
    assert resp.status_code == 200  # re-renders register form, does not redirect


def test_register_success_calls_create_user(client, monkeypatch):
    import routes.auth as auth_routes
    called = {}

    def fake_create_user(name, email, password, phone, club_id, role):
        called['args'] = (name, email, phone, club_id, role)
        return 42

    monkeypatch.setattr(auth_routes, 'create_user', fake_create_user)

    resp = client.post('/register', data={
        'name': 'New Student', 'email': 'new@cecrms.com',
        'phone': '9000000099', 'password': 'newpass123',
    }, follow_redirects=False)

    assert resp.status_code == 302
    assert called['args'] == ('New Student', 'new@cecrms.com', '9000000099', None, 'student')


def test_logout_clears_session(client):
    from tests.conftest import login_as
    login_as(client, role='admin')
    resp = client.get('/logout', follow_redirects=False)
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert 'user_id' not in sess


def test_dashboard_requires_login(client):
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_admin_only_route_blocks_student(client):
    from tests.conftest import login_as
    login_as(client, role='student')
    resp = client.get('/admin/coordinators', follow_redirects=True)
    assert resp.status_code == 200
    # admin_required redirects a non-admin to the dashboard instead of
    # rendering the admin page.
    assert resp.request.path == '/'


def test_admin_only_route_allows_admin(client):
    from tests.conftest import login_as
    login_as(client, role='admin')
    resp = client.get('/admin/coordinators', follow_redirects=True)
    assert resp.status_code == 200


# ── CSRF Regression Tests ──────────────────────────────────────────────────────
# These tests use a separate app/client fixture with CSRF *enabled* to guard
# against the regression where login.html / register.html lost their csrf_token
# hidden input (because they are standalone pages that do NOT extend layout.html
# and therefore never get the CSRF injector JS from layout.html).

@pytest.fixture
def csrf_app(fake_db):
    """App fixture with CSRF fully enabled (WTF_CSRF_ENABLED=True)."""
    from app import create_app
    application = create_app()
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_CHECK_DEFAULT=True,
        # Use a fixed SECRET_KEY so the token is reproducible within the session.
        SECRET_KEY='test-secret-key-csrf-regression',
    )
    return application


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


def test_login_page_contains_csrf_token(csrf_client):
    """GET /login must render a page containing a csrf_token input field."""
    resp = csrf_client.get('/login')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'csrf_token' in html, (
        "login.html does not contain a csrf_token field — "
        "POST /login will always return 400. Add "
        '`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`'
        " inside the <form> in login.html."
    )


def test_login_post_without_csrf_token_returns_400(csrf_client):
    """POST /login without a CSRF token must be rejected with HTTP 400."""
    resp = csrf_client.post(
        '/login',
        data={'email': 'user@test.com', 'password': 'secret'},
        follow_redirects=False,
    )
    assert resp.status_code == 400, (
        "Expected 400 (CSRF rejected) but got %d. "
        "CSRF protection may be accidentally disabled." % resp.status_code
    )


def test_login_post_with_valid_csrf_token_succeeds(csrf_client, monkeypatch):
    """POST /login with a valid CSRF token must proceed (not return 400)."""
    import routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, 'get_user_by_email', lambda e: FAKE_USER)

    # Step 1: GET the login page to obtain a valid session-bound CSRF token.
    get_resp = csrf_client.get('/login')
    assert get_resp.status_code == 200

    # Step 2: Extract the token from the rendered HTML.
    html = get_resp.data.decode()
    import re
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, (
        "Could not find csrf_token hidden input in login page HTML. "
        "The regression fix may not have been applied correctly."
    )
    token = match.group(1)

    # Step 3: POST with the valid token — should NOT be rejected by CSRF.
    post_resp = csrf_client.post(
        '/login',
        data={'email': 'asha@cecrms.com', 'password': 'student123', 'csrf_token': token},
        follow_redirects=False,
    )
    # 302 = successful login redirect; 200 = wrong-password re-render.
    # Both are acceptable — the key point is NOT 400 (CSRF rejection).
    assert post_resp.status_code != 400, (
        "POST /login returned 400 even with a valid CSRF token. "
        "Check that the csrf_token hidden input value is being read from {{ csrf_token() }}."
    )


def test_register_page_contains_csrf_token(csrf_client):
    """GET /register must render a page containing a csrf_token input field."""
    resp = csrf_client.get('/register')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'csrf_token' in html, (
        "register.html does not contain a csrf_token field — "
        "POST /register will always return 400."
    )


def test_register_post_without_csrf_token_returns_400(csrf_client):
    """POST /register without a CSRF token must be rejected with HTTP 400."""
    resp = csrf_client.post(
        '/register',
        data={'name': 'A', 'email': 'a@b.com', 'password': 'pass'},
        follow_redirects=False,
    )
    assert resp.status_code == 400, (
        "Expected 400 (CSRF rejected) but got %d." % resp.status_code
    )


def test_register_post_with_valid_csrf_token_proceeds(csrf_client, monkeypatch):
    """POST /register with a valid CSRF token must not be rejected by CSRF."""
    import routes.auth as auth_routes
    monkeypatch.setattr(auth_routes, 'create_user',
                        lambda name, email, password, phone, club_id, role: 99)

    get_resp = csrf_client.get('/register')
    html = get_resp.data.decode()
    import re
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, "csrf_token hidden input not found in register.html"
    token = match.group(1)

    post_resp = csrf_client.post(
        '/register',
        data={
            'name': 'New Student', 'email': 'new@cecrms.com',
            'password': 'pass123', 'csrf_token': token,
        },
        follow_redirects=False,
    )
    assert post_resp.status_code != 400, (
        "POST /register returned 400 even with a valid CSRF token."
    )
