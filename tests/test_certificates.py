"""Certificate generation: dedup behavior and search."""
import services.certificate_service as cert_service


def test_issue_certificate_returns_existing_without_regenerating(monkeypatch):
    existing = {'cert_id': 7, 'event_id': 1, 'user_id': 2, 'cert_path': 'certificates/cert_1_2.png'}
    monkeypatch.setattr(cert_service, 'certificate_exists', lambda event_id, user_id: existing)

    generated = {'called': False}
    def fake_gen_cert(**kwargs):
        generated['called'] = True
        return kwargs.get('save_path')
    monkeypatch.setattr(cert_service, '_gen_cert', fake_gen_cert)

    result = cert_service.issue_certificate(1, 2, 'Student Name', 'Workshop')
    assert result == existing
    assert generated['called'] is False  # never regenerates a duplicate


def test_search_certificates_scopes_to_own_for_students(monkeypatch, fake_db):
    captured = {}

    class FakeCursor:
        def execute(self, query, params):
            captured['query'] = query
            captured['params'] = params
        def fetchall(self):
            return []
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr('services.certificate_service.get_db_connection', lambda: FakeConn())
    cert_service.search_certificates('workshop', user_id=42, role='student')
    assert 'cert.user_id = %s' in captured['query']
    assert 42 in captured['params']


def test_search_certificates_admin_searches_everyone(monkeypatch):
    captured = {}

    class FakeCursor:
        def execute(self, query, params):
            captured['query'] = query
        def fetchall(self):
            return []
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr('services.certificate_service.get_db_connection', lambda: FakeConn())
    cert_service.search_certificates('workshop', user_id=1, role='admin')
    assert 'cert.user_id = %s' not in captured['query']
