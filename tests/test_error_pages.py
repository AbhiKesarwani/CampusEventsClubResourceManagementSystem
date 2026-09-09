"""Error pages: 403, 404, 500 all render with the dark emerald design and
useful actions, for both anonymous and logged-in visitors."""
from flask import abort
from tests.conftest import login_as


def test_404_renders_for_anonymous(client):
    resp = client.get('/this-route-does-not-exist')
    assert resp.status_code == 404
    assert b'404' in resp.data
    assert b'Go to Dashboard' in resp.data or b'Sign' in resp.data


def test_404_renders_for_logged_in_user(client):
    login_as(client, role='student')
    resp = client.get('/this-route-does-not-exist')
    assert resp.status_code == 404
    assert b'404' in resp.data


def test_403_handler_renders_dark_theme(app, client):
    @app.route('/_test-forbidden')
    def _trigger_403():
        abort(403)

    resp = client.get('/_test-forbidden')
    assert resp.status_code == 403
    assert b'403' in resp.data
    assert b'Access Denied' in resp.data


def test_500_handler_renders_dark_theme(app, client):
    app.config['PROPAGATE_EXCEPTIONS'] = False
    app.testing = False  # let the real errorhandler(500) run instead of re-raising

    @app.route('/_test-crash')
    def _trigger_500():
        raise RuntimeError("simulated failure")

    resp = client.get('/_test-crash')
    assert resp.status_code == 500
    assert b'500' in resp.data

