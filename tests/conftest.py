"""Shared pytest fixtures for the CECRMS test suite.

Tests never hit a real MySQL server — `database.get_db_connection` is
monkeypatched with a lightweight fake connection/cursor that returns empty
results by default. Individual tests monkeypatch specific service
functions when they need particular data, which is more robust than trying
to script raw SQL cursor responses.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Ensure no real OpenRouter calls are ever attempted during tests, even
# though the developer's real .env may define a working key. This module-
# level pop only covers the collection phase — dotenv can silently re-add
# it later (e.g. when config.py/database.py call load_dotenv() the first
# time app.py is imported inside a fixture), so it's reinforced by the
# autouse `no_openrouter_calls` fixture below, which runs immediately
# before every single test body.
os.environ.pop('OPENROUTER_API_KEY', None)


@pytest.fixture(autouse=True)
def no_openrouter_calls(monkeypatch):
    """Guarantee OPENROUTER_API_KEY is absent for the body of every test,
    regardless of what the developer's local .env defines or when dotenv
    happens to (re)populate it during import. Without this, a real key in
    .env would make services.ai_service actually call the live OpenRouter
    API during test runs."""
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

    # Also reset ai_service's module-level state between tests — both are
    # plain in-process dicts that would otherwise leak stale data (a cached
    # bad response, or a rate-limit counter) across unrelated test cases.
    import services.ai_service as ai_service
    ai_service._AI_CACHE.clear()
    ai_service._rate_log.clear()



class FakeCursor:
    """Minimal DB-API cursor stand-in. Returns empty results for everything
    unless a test monkeypatches the service function that would have used
    the real data.

    fetchone() returns (0,) for plain (non-dict) cursors — this mirrors real
    MySQL, where an aggregate query like `SELECT COUNT(*) FROM x` always
    returns exactly one row (never NULL/no-row) even when the count is zero.
    Dict cursors (used for entity lookups like `SELECT * FROM users WHERE
    id=%s`) return None, matching a genuine "not found" — which the app
    already handles defensively (e.g. `if not user: ...`).
    """

    def __init__(self, dictionary=False):
        self.dictionary = dictionary
        self.rowcount = 0
        self.lastrowid = 1

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return []

    def fetchone(self):
        return None if self.dictionary else (0,)

    def close(self):
        pass


class FakeConnection:
    def cursor(self, dictionary=False):
        return FakeCursor(dictionary=dictionary)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def fake_db(monkeypatch):
    """Monkeypatch database.get_db_connection everywhere it's imported.

    Most service modules (and routes/search.py) do
    `from database import get_db_connection`, which binds their own local
    name to the original function object — patching `database`'s attribute
    alone does NOT affect those modules. Every module holding such a local
    binding must be patched individually.
    """
    import database
    fake = lambda: FakeConnection()
    monkeypatch.setattr(database, 'get_db_connection', fake)

    modules_with_local_import = [
        'services.ai_service', 'services.attendance_service', 'services.club_service',
        'services.certificate_service', 'services.connect_service', 'services.event_service',
        'services.log_service', 'services.membership_service', 'services.recommendation_service',
        'services.notification_service', 'services.member_service', 'services.user_service',
        'services.resource_service', 'services.venue_service', 'routes.search',
    ]
    import importlib
    for mod_name in modules_with_local_import:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, 'get_db_connection'):
            monkeypatch.setattr(mod, 'get_db_connection', fake)

    return FakeConnection


@pytest.fixture
def app(fake_db):
    from app import create_app
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, user_id=1, role='student', name="Test User", email="test@example.com", club_id=None):
    """Helper: populate a logged-in session for the given role."""
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['role'] = role
        sess['name'] = name
        sess['email'] = email
        sess['club_id'] = club_id
