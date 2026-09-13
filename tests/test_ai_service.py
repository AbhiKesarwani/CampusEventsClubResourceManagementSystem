"""AI service: intent detection, rate limiting, and pipeline behavior."""
import services.ai_service as ai_service


def test_detect_intent_event():
    # Note: the intent patterns use \bevent\b (singular, word-boundary), so
    # plural-only phrasing like "events" alone won't match — this mirrors
    # the real regex behavior in services/ai_service.py.
    assert ai_service.detect_intent("When is the next event?") == 'event'


def test_detect_intent_club():
    assert ai_service.detect_intent("Tell me about the Robotics club") == 'club'


def test_detect_intent_attendance():
    assert ai_service.detect_intent("How do I mark my attendance with OTP?") == 'attendance'


def test_detect_intent_certificate():
    assert ai_service.detect_intent("Where can I download my certificate?") == 'certificate'


def test_detect_intent_venue():
    assert ai_service.detect_intent("What's the capacity of the auditorium?") == 'venue'


def test_detect_intent_general_fallback():
    assert ai_service.detect_intent("Write me a poem about the ocean") == 'general'


def test_rate_limit_allows_under_threshold():
    ai_service._rate_log.clear()
    for _ in range(ai_service._RATE_MAX_CALLS):
        assert ai_service.check_rate_limit(user_id=999) is True


def test_rate_limit_blocks_over_threshold():
    ai_service._rate_log.clear()
    for _ in range(ai_service._RATE_MAX_CALLS):
        ai_service.check_rate_limit(user_id=999)
    assert ai_service.check_rate_limit(user_id=999) is False


def test_rate_limit_is_per_user():
    ai_service._rate_log.clear()
    for _ in range(ai_service._RATE_MAX_CALLS):
        ai_service.check_rate_limit(user_id=1)
    # A different user is unaffected by user 1's rate limit.
    assert ai_service.check_rate_limit(user_id=2) is True


def test_campus_connect_ai_empty_question_returns_error():
    result = ai_service.campus_connect_ai('   ', user_id=1)
    assert result['source'] == 'error'
    assert result['escalate'] is False


def test_campus_connect_ai_general_question_never_escalates_without_key(fake_db):
    ai_service._rate_log.clear()
    # No OPENROUTER_API_KEY set (conftest strips it) -> graceful "not configured"
    # message from the OpenRouter fallback path, never a crash.
    result = ai_service.campus_connect_ai("Write me a poem about the ocean", user_id=1)
    assert result['intent'] == 'general'
    assert result['escalate'] is False  # general intent is excluded from escalation
    assert 'not configured' in result['answer'].lower()


def test_campus_connect_ai_rate_limited_message(fake_db):
    ai_service._rate_log.clear()
    for _ in range(ai_service._RATE_MAX_CALLS):
        ai_service.check_rate_limit(user_id=55)
    result = ai_service.campus_connect_ai("When is the next event?", user_id=55)
    assert result['source'] == 'error'
    assert 'fast' in result['answer'].lower()
