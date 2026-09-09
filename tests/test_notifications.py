"""Notifications: dedup via event_key, unread counts, and route behavior."""
import services.notification_service as notif_service
from tests.conftest import login_as


def test_create_notification_safe_uses_insert_ignore_with_event_key(monkeypatch):
    captured = {}

    class FakeCursor:
        def __init__(self):
            self.rowcount = 1
        def execute(self, query, params):
            captured['query'] = query
            captured['params'] = params
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass

    monkeypatch.setattr(notif_service, 'get_db_connection', lambda: FakeConn())

    result = notif_service.create_notification_safe(
        user_id=1, title='Test', body='Body', link='/x',
        type='info', event_key='unique_key_123'
    )
    assert result is True
    assert 'INSERT IGNORE' in captured['query']
    assert 'unique_key_123' in captured['params']


def test_create_notification_safe_without_event_key_falls_back_to_plain_insert(monkeypatch):
    calls = {'plain_insert': False}

    def fake_create_notification(user_id, title, body=None, link=None, type='info'):
        calls['plain_insert'] = True

    monkeypatch.setattr(notif_service, 'create_notification', fake_create_notification)
    result = notif_service.create_notification_safe(user_id=1, title='Test')
    assert result is True
    assert calls['plain_insert'] is True


def test_notifications_page_requires_login(client):
    resp = client.get('/notifications/', follow_redirects=False)
    assert resp.status_code == 302


def test_notifications_page_renders(client):
    login_as(client, role='student')
    resp = client.get('/notifications/')
    assert resp.status_code == 200


def test_mark_all_read_route(client):
    login_as(client, role='student')
    resp = client.post('/notifications/mark-all-read', follow_redirects=True)
    assert resp.status_code == 200
