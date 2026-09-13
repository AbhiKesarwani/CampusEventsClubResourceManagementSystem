"""Regression tests for AI service (ai_service.py).

Guards against:
1. Intent detection misclassifying common questions as 'general'.
2. OpenRouter model configuration issues.
3. answer_from_db returning None when DB has data (SQL correctness).
4. campus_connect_ai pipeline structure (source/intent/escalate/confidence keys).
5. Rate limiting working correctly.
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Intent Detection ────────────────────────────────────────────────────────────

class TestIntentDetection:
    """Every listed query must NOT classify as 'general'."""

    @pytest.mark.parametrize('question,expected_intent', [
        # Events
        ('What are the upcoming events?', 'event'),
        ('upcoming events', 'event'),
        ('list all events', 'event'),
        ('what events are happening today', 'event'),
        ("today's schedule", 'event'),
        # Clubs
        ('Show me clubs', 'club'),
        ('list clubs', 'club'),
        ('what clubs are there?', 'club'),
        ('which club should I join?', 'club'),
        ('club members', 'club'),
        # Venues — avoid 'available' which also matches resource intent
        ('List venues', 'venue'),
        ('show me halls', 'venue'),
        ('auditorium capacity', 'venue'),
        ('venue locations on campus', 'venue'),
        # Certificates
        ('my certificates', 'certificate'),
        ('show my awards', 'certificate'),
        ('I want to download my certificate', 'certificate'),
        # Coordinators
        ('coordinators list', 'coordinator'),
        ('show coordinators', 'coordinator'),
        # Attendance
        ('what is my attendance?', 'attendance'),
        ('check my attendance', 'attendance'),
        # Announcements
        ('recent announcements', 'announcement'),
        ('latest news', 'announcement'),
    ])
    def test_intent_not_general(self, question, expected_intent, fake_db):
        from services.ai_service import detect_intent
        result = detect_intent(question)
        assert result == expected_intent, (
            f"detect_intent({question!r}) returned {result!r}, expected {expected_intent!r}. "
            f"Add missing keyword patterns to _INTENT_PATTERNS['{expected_intent}']."
        )

    def test_greetings_classified_general(self, fake_db):
        from services.ai_service import detect_intent
        # Greetings and off-topic questions must remain 'general'
        for q in ['Hello', 'Hi there', 'Tell me a joke', 'What is 2+2?']:
            assert detect_intent(q) == 'general', f"'{q}' should be 'general'"


# ── AI Pipeline Structure ───────────────────────────────────────────────────────

class TestCampusConnectAiPipeline:
    def test_returns_required_keys(self, fake_db, monkeypatch):
        """campus_connect_ai must always return dict with all required keys."""
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'answer_from_db', lambda intent, q, uid: ('DB answer', 0.95))
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: True)

        result = svc.campus_connect_ai('upcoming events', user_id=1)
        for key in ('answer', 'source', 'intent', 'escalate', 'confidence'):
            assert key in result, f"Missing key '{key}' in campus_connect_ai result"

    def test_db_first_when_high_confidence(self, fake_db, monkeypatch):
        """When DB answer has confidence >= 0.8, source must be 'db'."""
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'answer_from_db', lambda intent, q, uid: ('Found it', 0.95))
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: True)

        result = svc.campus_connect_ai('clubs', user_id=1)
        assert result['source'] == 'db', "High-confidence DB answer should set source='db'"
        assert result['answer'] == 'Found it'
        assert result['escalate'] is False

    def test_falls_back_to_openrouter_when_db_low_confidence(self, fake_db, monkeypatch):
        """When DB confidence < 0.8, should call OpenRouter."""
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'answer_from_db', lambda intent, q, uid: (None, 0.0))
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: True)
        monkeypatch.setattr(svc, 'answer_from_openrouter',
                            lambda msgs, **kw: ('AI says hello', 0.8))

        result = svc.campus_connect_ai('tell me about events', user_id=1)
        assert result['source'] == 'ai'
        assert result['answer'] == 'AI says hello'

    def test_empty_question_returns_error(self, fake_db, monkeypatch):
        import services.ai_service as svc
        result = svc.campus_connect_ai('   ', user_id=1)
        assert result['source'] == 'error'

    def test_rate_limit_exceeded_returns_error(self, fake_db, monkeypatch):
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: False)
        result = svc.campus_connect_ai('hello', user_id=99)
        assert result['source'] == 'error'
        assert 'too fast' in result['answer'].lower() or 'wait' in result['answer'].lower()

    def test_escalate_flag_false_for_high_confidence(self, fake_db, monkeypatch):
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'answer_from_db', lambda intent, q, uid: ('answer', 0.95))
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: True)
        result = svc.campus_connect_ai('clubs', user_id=1)
        assert result['escalate'] is False

    def test_escalate_flag_true_for_low_confidence_non_general(self, fake_db, monkeypatch):
        import services.ai_service as svc
        monkeypatch.setattr(svc, 'answer_from_db', lambda intent, q, uid: (None, 0.0))
        monkeypatch.setattr(svc, 'check_rate_limit', lambda uid: True)
        # Return low-confidence AI answer for a specific intent (not 'general')
        monkeypatch.setattr(svc, 'answer_from_openrouter',
                            lambda msgs, **kw: ('Uncertain', 0.3))
        result = svc.campus_connect_ai('club membership process', user_id=1)
        # club intent + low confidence → escalate = True
        assert result['escalate'] is True


# ── OpenRouter Model Config ─────────────────────────────────────────────────────

class TestOpenRouterConfig:
    def test_no_api_key_returns_error_message(self, fake_db, monkeypatch):
        """Without API key, should return a friendly error, not crash."""
        import services.ai_service as svc
        import os
        monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

        answer, conf = svc.answer_from_openrouter([{'role': 'user', 'content': 'hello'}])
        assert 'not configured' in answer.lower() or 'contact' in answer.lower()
        assert conf == 0.0

    def test_model_default_not_discontinued(self, fake_db):
        """Default model must not be the discontinued google/gemini-flash-1.5."""
        import os
        import services.ai_service as svc
        import importlib
        # The default model in the source should not be the known-dead model
        import inspect
        source = inspect.getsource(svc.answer_from_openrouter)
        assert 'google/gemini-flash-1.5' not in source or 'gpt-4o-mini' in source, (
            "Default OpenRouter model is still google/gemini-flash-1.5 which returns 404. "
            "Update to openai/gpt-4o-mini or set OPENROUTER_MODEL env var."
        )

    def test_fallback_models_included(self, monkeypatch):
        """Fallback models should be appended and duplicates pruned."""
        import services.ai_service as svc
        monkeypatch.setenv('OPENROUTER_MODEL', 'custom/primary-model')
        models = svc.get_openrouter_models()
        assert models[0] == 'custom/primary-model'
        assert 'openai/gpt-4o-mini' in models
        assert 'google/gemini-2.5-flash' in models
        assert len(models) > 3

    def test_comma_separated_models(self, monkeypatch):
        """Comma-separated models in env should all be respected in order."""
        import services.ai_service as svc
        monkeypatch.setenv('OPENROUTER_MODEL', 'model-a, model-b')
        monkeypatch.setenv('OPENROUTER_FALLBACK_MODELS', 'model-c, model-d')
        models = svc.get_openrouter_models()
        assert models[:4] == ['model-a', 'model-b', 'model-c', 'model-d']

    def test_multi_model_payload_used_in_request(self, monkeypatch):
        """Requests to OpenRouter should include the models fallback array capped at 3."""
        import services.ai_service as svc
        captured_payload = {}

        class DummyResponse:
            status_code = 200
            def json(self):
                return {'choices': [{'message': {'content': 'ok'}}], 'model': 'test-model'}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured_payload.update(json)
            return DummyResponse()

        monkeypatch.setenv('OPENROUTER_API_KEY', 'dummy-key')
        monkeypatch.setenv('OPENROUTER_MODEL', 'primary-model, fallback-1, fallback-2, fallback-3')
        import requests
        monkeypatch.setattr(requests, 'post', fake_post)

        answer, conf = svc.answer_from_openrouter([{'role': 'user', 'content': 'test'}])
        assert answer == 'ok'
        assert captured_payload['model'] == 'primary-model'
        assert captured_payload['models'] == ['primary-model', 'fallback-1', 'fallback-2']
        assert len(captured_payload['models']) <= 3



# ── answer_from_db SQL correctness ─────────────────────────────────────────────

class TestAnswerFromDb:
    """Verify DB queries don't crash and return correct structure."""

    @pytest.mark.parametrize('intent', [
        'event', 'club', 'venue',
        'attendance', 'certificate', 'coordinator', 'announcement',
    ])
    def test_answer_from_db_does_not_crash(self, intent, fake_db, monkeypatch):
        """Every intent path in answer_from_db must handle an empty DB gracefully."""
        import services.ai_service as svc
        monkeypatch.setattr(svc, '_run_query', lambda sql, params=(): [])
        ans, conf = svc.answer_from_db(intent, 'test question', user_id=1)
        # With empty DB: either returns None or a "no X found" string
        assert ans is None or isinstance(ans, str)
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_event_today_with_data(self, fake_db, monkeypatch):
        import services.ai_service as svc
        mock_rows = [{'title': 'Tech Talk', 'start_time': '10:00:00', 'end_time': '12:00:00',
                      'venue_name': 'Hall A', 'club_name': 'Tech Club'}]
        monkeypatch.setattr(svc, '_run_query', lambda sql, params=(): mock_rows)
        ans, conf = svc.answer_from_db('event', "today's events", user_id=1)
        assert ans is not None
        assert 'Tech Talk' in ans
        assert conf >= 0.8

    def test_club_with_data(self, fake_db, monkeypatch):
        import services.ai_service as svc
        mock_rows = [{'club_name': 'Coding Club', 'description': 'We code',
                      'coordinator_name': 'Alice', 'member_count': 15}]
        monkeypatch.setattr(svc, '_run_query', lambda sql, params=(): mock_rows)
        ans, conf = svc.answer_from_db('club', 'show clubs', user_id=1)
        assert ans is not None
        assert 'Coding Club' in ans
        assert conf >= 0.8

    def test_attendance_empty(self, fake_db, monkeypatch):
        import services.ai_service as svc
        monkeypatch.setattr(svc, '_run_query', lambda sql, params=(): [])
        ans, conf = svc.answer_from_db('attendance', 'my attendance', user_id=99)
        assert ans is not None  # "no attendance yet" message
        assert conf >= 0.8

    def test_certificate_empty(self, fake_db, monkeypatch):
        import services.ai_service as svc
        monkeypatch.setattr(svc, '_run_query', lambda sql, params=(): [])
        ans, conf = svc.answer_from_db('certificate', 'my certificates', user_id=99)
        assert ans is not None
        assert conf >= 0.8


# ── Rate Limiting ───────────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_within_limit(self, fake_db):
        from services.ai_service import check_rate_limit, _rate_log
        _rate_log.clear()
        for _ in range(19):
            assert check_rate_limit(9999) is True

    def test_exceeds_limit(self, fake_db):
        from services.ai_service import check_rate_limit, _RATE_MAX_CALLS, _rate_log
        _rate_log.clear()
        uid = 9998
        for _ in range(_RATE_MAX_CALLS):
            check_rate_limit(uid)
        # Next call should be rejected
        assert check_rate_limit(uid) is False
