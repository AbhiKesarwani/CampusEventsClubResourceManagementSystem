"""Regression test: services.resource_service.approve_request/reject_request
must NOT fire their own notification — routes/resources.py already sends a
deduplicated one via create_notification_safe(). Firing both would double
the notification (a real bug fixed in a previous cleanup pass)."""
import services.resource_service as resource_service


class _FakeCursorApprove:
    """Simulates: SELECT pending request -> SELECT stock -> UPDATE -> INSERT event_resources."""
    def __init__(self):
        self.calls = 0

    def execute(self, query, params=None):
        self.calls += 1

    def fetchone(self):
        if self.calls == 1:
            return {'request_id': 1, 'event_id': 1, 'club_id': 1, 'resource_id': 1,
                    'quantity': 2, 'requested_by': 5, 'resource_name': 'Projector',
                    'event_title': 'Robo Wars'}
        if self.calls == 2:
            return {'total_quantity': 10, 'allocated': 0}
        return None

    def close(self):
        pass


class _FakeConn:
    def __init__(self):
        self._cur = _FakeCursorApprove()

    def cursor(self, dictionary=False):
        return self._cur

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def test_approve_request_does_not_send_its_own_notification(monkeypatch):
    monkeypatch.setattr(resource_service, 'get_db_connection', lambda: _FakeConn())

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "approve_request must not call create_notification directly — "
            "routes/resources.py already sends a deduplicated notification."
        )

    import services.notification_service as notif_service
    monkeypatch.setattr(notif_service, 'create_notification', _fail_if_called)

    # Should not raise — proves no duplicate notification path is exercised.
    resource_service.approve_request(request_id=1, reviewed_by=1)


def test_reject_request_does_not_send_its_own_notification(monkeypatch):
    class _FakeRejectCursor:
        def execute(self, query, params=None):
            pass

        def fetchone(self):
            return {'request_id': 1, 'event_id': 1, 'quantity': 2,
                    'requested_by': 5, 'resource_name': 'Projector', 'event_title': 'Robo Wars'}

        def close(self):
            pass

    class _FakeRejectConn:
        def cursor(self, dictionary=False):
            return _FakeRejectCursor()

        def commit(self): pass
        def rollback(self): pass
        def close(self): pass

    monkeypatch.setattr(resource_service, 'get_db_connection', lambda: _FakeRejectConn())

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("reject_request must not call create_notification directly.")

    import services.notification_service as notif_service
    monkeypatch.setattr(notif_service, 'create_notification', _fail_if_called)

    resource_service.reject_request(request_id=1, reviewed_by=1)
