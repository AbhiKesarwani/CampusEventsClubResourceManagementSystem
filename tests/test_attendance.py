"""OTP attendance logic: generation format, expiry, and self-submit flow."""
import re
from datetime import datetime, timedelta

import services.attendance_service as attendance_service


def test_generate_otp_digits_is_six_digits():
    otp = attendance_service._generate_otp_digits()
    assert re.fullmatch(r'\d{6}', otp)


def test_generate_code_format():
    code = attendance_service._generate_code()
    assert re.fullmatch(r'[A-Z]{3}-\d{6}', code)


def test_get_event_by_otp_expired_returns_none(monkeypatch):
    stale_event = {
        'event_id': 5, 'title': 'Old Workshop',
        'attendance_otp': '123456',
        'otp_generated_at': datetime.now() - timedelta(minutes=10),
    }

    class FakeCursor:
        def execute(self, *a, **k): pass
        def fetchone(self): return stale_event
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr('services.attendance_service.get_db_connection', lambda: FakeConn())
    assert attendance_service.get_event_by_otp('123456') is None


def test_get_event_by_otp_valid_within_window(monkeypatch):
    fresh_event = {
        'event_id': 5, 'title': 'Fresh Workshop',
        'attendance_otp': '654321',
        'otp_generated_at': datetime.now() - timedelta(minutes=2),
    }

    class FakeCursor:
        def execute(self, *a, **k): pass
        def fetchone(self): return fresh_event
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr('services.attendance_service.get_db_connection', lambda: FakeConn())
    result = attendance_service.get_event_by_otp('654321')
    assert result is not None
    assert result['title'] == 'Fresh Workshop'


def test_submit_otp_self_invalid_otp(monkeypatch):
    monkeypatch.setattr(attendance_service, 'get_event_by_otp', lambda otp: None)
    result = attendance_service.submit_otp_self('000000', user_id=1)
    assert result['success'] is False
    assert 'Invalid or expired' in result['message']


def test_submit_otp_self_already_marked(monkeypatch):
    monkeypatch.setattr(attendance_service, 'get_event_by_otp',
                        lambda otp: {'event_id': 1, 'title': 'Workshop'})
    monkeypatch.setattr(attendance_service, 'mark_attendance', lambda *a, **k: False)
    result = attendance_service.submit_otp_self('123456', user_id=1)
    assert result['success'] is False
    assert 'already submitted' in result['message']


def test_submit_otp_self_success_issues_certificate(monkeypatch, fake_db):
    monkeypatch.setattr(attendance_service, 'get_event_by_otp',
                        lambda otp: {'event_id': 1, 'title': 'Workshop'})
    monkeypatch.setattr(attendance_service, 'mark_attendance', lambda *a, **k: True)

    import services.certificate_service as cert_service
    import services.user_service as user_service
    monkeypatch.setattr(cert_service, 'issue_certificate',
                        lambda *a, **k: {'cert_path': 'certificates/cert_1_1.png'})
    monkeypatch.setattr(user_service, 'get_user_by_id',
                        lambda uid: {'user_id': uid, 'name': 'Test Student'})

    result = attendance_service.submit_otp_self('123456', user_id=1)
    assert result['success'] is True
    assert result['event_title'] == 'Workshop'
    assert result['cert_path'] == 'certificates/cert_1_1.png'
