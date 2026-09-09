"""Direct unit tests for the RBAC decorators in helpers/auth_helpers.py,
exercised against real routes decorated with them."""


def test_login_required_redirects_when_anonymous(app):
    with app.test_client() as client:
        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']


def test_login_required_allows_authenticated(app):
    from tests.conftest import login_as
    with app.test_client() as client:
        login_as(client, role='student')
        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 200


def test_club_admin_required_blocks_student(app):
    from tests.conftest import login_as
    with app.test_client() as client:
        login_as(client, role='student')
        resp = client.get('/events/create', follow_redirects=True)
        assert resp.status_code == 200
        assert resp.request.path == '/'  # bounced to dashboard


def test_club_admin_required_allows_coordinator(app):
    from tests.conftest import login_as
    with app.test_client() as client:
        login_as(client, role='club_admin', club_id=3)
        resp = client.get('/events/create', follow_redirects=True)
        assert resp.status_code == 200
        assert resp.request.path == '/events/create'
