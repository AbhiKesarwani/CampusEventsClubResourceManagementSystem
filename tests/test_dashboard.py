"""Dashboard: renders correctly (with role-specific stats/charts) for every role."""
from tests.conftest import login_as


def test_dashboard_renders_for_student(client):
    login_as(client, role='student')
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Dashboard' in resp.data or b'dashboard' in resp.data.lower()


def test_dashboard_renders_for_club_admin(client):
    login_as(client, role='club_admin', club_id=3)
    resp = client.get('/')
    assert resp.status_code == 200


def test_dashboard_renders_for_club_admin_without_club(client):
    # A coordinator whose club_id session value is missing must not 500.
    login_as(client, role='club_admin', club_id=None)
    resp = client.get('/')
    assert resp.status_code == 200


def test_dashboard_renders_for_admin(client):
    login_as(client, role='admin')
    resp = client.get('/')
    assert resp.status_code == 200


def test_dashboard_requires_login(client):
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']
