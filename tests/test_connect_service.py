"""Regression tests for Campus Connect service layer (connect_service.py).

These tests specifically guard against:
1. SQL placeholder/parameter count mismatches (the get_inbox bug).
2. Missing cc_conversation_state table references breaking at runtime.
3. None club_id values causing issues in announcement queries.
4. send_message → RBAC → notification pipeline.

Tests use the project's FakeDB fixture (no real MySQL needed).
"""
import pytest
from unittest.mock import patch, MagicMock, call


# ── helpers ──────────────────────────────────────────────────────────────────

def make_fake_conn(rows=None, rowcount=0, lastrowid=1, dictionary=True):
    """Return a (conn, cur) pair backed by simple mocks."""
    cur = MagicMock()
    cur.fetchall.return_value = rows if rows is not None else []
    cur.fetchone.return_value = (0,) if not dictionary else None
    cur.lastrowid = lastrowid
    cur.rowcount = rowcount
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


# ── get_inbox ─────────────────────────────────────────────────────────────────

class TestGetInbox:
    """Verify get_inbox sends exactly 8 parameters to the DB for a normal call,
    and exactly 8 when include_archived=True (same query, same param count)."""

    def test_get_inbox_sends_correct_param_count(self, fake_db, monkeypatch):
        """The SQL in get_inbox has 8 %%s placeholders — must supply exactly 8 params."""
        import services.connect_service as svc
        executed_calls = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.fetchone.return_value = (0,)

            def capture_execute(sql, params=None):
                executed_calls.append((sql, params))
            cur.execute.side_effect = capture_execute
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)

        svc.get_inbox(user_id=42)

        # There should be at least one execute call (the main SELECT)
        assert executed_calls, "get_inbox made no execute() calls"

        # Find the main inbox query (it's the f-string one with ROW_NUMBER)
        inbox_calls = [(sql, params) for sql, params in executed_calls
                       if 'ROW_NUMBER' in (sql or '')]
        assert inbox_calls, "Could not find the get_inbox main query in execute calls"

        sql, params = inbox_calls[0]
        placeholder_count = sql.count('%s')
        param_count = len(params) if params else 0

        assert placeholder_count == param_count, (
            f"get_inbox SQL has {placeholder_count} %%s placeholders "
            f"but {param_count} parameters were passed. "
            f"This is the regression — mismatch causes ProgrammingError."
        )
        assert placeholder_count == 8, (
            f"Expected exactly 8 %%s in get_inbox query, found {placeholder_count}"
        )

    def test_get_inbox_with_include_archived_same_param_count(self, fake_db, monkeypatch):
        """include_archived=True uses same param count (conditional only changes SQL text,
        not the parameter tuple)."""
        import services.connect_service as svc
        executed_calls = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.fetchone.return_value = (0,)

            def capture_execute(sql, params=None):
                executed_calls.append((sql, params))
            cur.execute.side_effect = capture_execute
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.get_inbox(user_id=42, include_archived=True)

        inbox_calls = [(sql, params) for sql, params in executed_calls
                       if 'ROW_NUMBER' in (sql or '')]
        assert inbox_calls
        sql, params = inbox_calls[0]
        assert sql.count('%s') == len(params), (
            "include_archived=True path has mismatched placeholders vs params"
        )

    def test_get_inbox_returns_list(self, fake_db, monkeypatch):
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'get_db_connection',
                            lambda: MagicMock(cursor=lambda **kw: MagicMock(
                                fetchall=lambda: [], fetchone=lambda: (0,),
                                execute=lambda *a, **kw: None,
                                close=lambda: None)))
        # Should not raise — returns empty list when DB is empty
        result = svc.get_inbox(99)
        assert isinstance(result, list)


# ── get_conversation ───────────────────────────────────────────────────────────

class TestGetConversation:
    def test_placeholder_count(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed_calls = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed_calls.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.get_conversation(1, 2)

        for sql, params in executed_calls:
            if sql and 'cc_messages' in sql and params:
                ps = sql.count('%s')
                assert ps == len(params), (
                    f"get_conversation: {ps} placeholders but {len(params)} params"
                )

    def test_returns_list(self, fake_db, monkeypatch):
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'get_db_connection',
                            lambda: MagicMock(cursor=lambda **kw: MagicMock(
                                fetchall=lambda: [],
                                execute=lambda *a, **kw: None,
                                close=lambda: None)))
        assert isinstance(svc.get_conversation(1, 2), list)


# ── count_conversation ─────────────────────────────────────────────────────────

class TestCountConversation:
    def test_placeholder_count(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed_calls = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = (0,)
            cur.execute.side_effect = lambda sql, params=None: executed_calls.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.count_conversation(1, 2)

        for sql, params in executed_calls:
            if sql and params:
                ps = sql.count('%s')
                assert ps == len(params), f"count_conversation mismatch: {ps} vs {len(params)}"


# ── send_message ───────────────────────────────────────────────────────────────

class TestSendMessage:
    def test_empty_body_raises(self, fake_db, monkeypatch):
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'can_message', lambda s, r: True)
        with pytest.raises(ValueError, match="empty"):
            svc.send_message(1, 2, '   ')

    def test_rbac_rejected(self, fake_db, monkeypatch):
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'can_message', lambda s, r: False)
        with pytest.raises(PermissionError):
            svc.send_message(1, 2, 'hello')

    def test_successful_send_returns_int(self, fake_db, monkeypatch):
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'can_message', lambda s, r: True)
        monkeypatch.setattr(svc, 'create_notification_safe', lambda **kw: None)

        calls = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.lastrowid = 7
            cur.execute.side_effect = lambda sql, params=None: calls.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        result = svc.send_message(1, 2, 'Hello there', notify=False)
        assert result == 7

    def test_send_message_placeholder_counts(self, fake_db, monkeypatch):
        """Every INSERT in send_message must have matching placeholder counts."""
        import services.connect_service as svc
        monkeypatch.setattr(svc, 'can_message', lambda s, r: True)
        monkeypatch.setattr(svc, 'create_notification_safe', lambda **kw: None)
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.lastrowid = 1
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.send_message(1, 2, 'test', notify=False)

        for sql, params in executed:
            if params and sql:
                ps = sql.count('%s')
                assert ps == len(params), (
                    f"send_message SQL mismatch: {ps} placeholders, {len(params)} params\n"
                    f"SQL: {sql[:120]}"
                )


# ── Announcements ──────────────────────────────────────────────────────────────

class TestAnnouncements:
    def test_get_announcements_admin_no_params_needed(self, fake_db, monkeypatch):
        """Admin query has 2 params (LIMIT, OFFSET) — no role or club_id needed."""
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.get_announcements_for_user(1, 'admin', None)

        for sql, params in executed:
            if sql and 'cc_announcements' in sql and params:
                assert sql.count('%s') == len(params), (
                    f"Admin announcement query: {sql.count('%s')} vs {len(params)}"
                )

    def test_get_announcements_student_none_club_id(self, fake_db, monkeypatch):
        """get_announcements_for_user with role='student' and club_id=None
        should not crash — None is a valid SQL NULL param."""
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        # Should not raise
        result = svc.get_announcements_for_user(99, 'student', None)
        assert isinstance(result, list)

        for sql, params in executed:
            if sql and 'cc_announcements' in sql and params:
                assert sql.count('%s') == len(params), (
                    f"Student announcement query mismatch: "
                    f"{sql.count('%s')} vs {len(params)}"
                )

    def test_get_announcements_student_with_club_id(self, fake_db, monkeypatch):
        """Same test with a valid club_id."""
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.get_announcements_for_user(99, 'student', 5)

        for sql, params in executed:
            if sql and 'cc_announcements' in sql and params:
                assert sql.count('%s') == len(params)

    def test_count_announcements_student(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = (0,)
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.count_announcements_for_user(99, 'student', None)

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params)


# ── AI history ─────────────────────────────────────────────────────────────────

class TestAiHistory:
    def test_save_ai_message_placeholder_count(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.save_ai_message(1, 'user', 'hello', 'db')

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params)

    def test_get_ai_history_placeholder_count(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.get_ai_history(1, limit=10)

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params)

    def test_clear_ai_history_placeholder_count(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.clear_ai_history(1)

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params)


# ── Unread count ──────────────────────────────────────────────────────────────

class TestUnreadCount:
    def test_count_unread_messages(self, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = (3,)
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        result = svc.count_unread_messages(42)
        assert result == 3

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params)


# ── Search contacts ────────────────────────────────────────────────────────────

class TestSearchContacts:
    @pytest.mark.parametrize('role,club_id', [
        ('admin', None),
        ('club_admin', 4),
        ('student', None),
    ])
    def test_placeholder_count(self, role, club_id, fake_db, monkeypatch):
        import services.connect_service as svc
        executed = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchall.return_value = []
            cur.execute.side_effect = lambda sql, params=None: executed.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.search_contacts('test', 1, role, club_id)

        for sql, params in executed:
            if sql and params:
                assert sql.count('%s') == len(params), (
                    f"search_contacts role={role}: "
                    f"{sql.count('%s')} placeholders, {len(params)} params"
                )

    def test_coordinator_without_club_returns_empty(self, fake_db, monkeypatch):
        import services.connect_service as svc
        result = svc.search_contacts('x', 1, 'club_admin', None)
        assert result == []


# ── AI history source ENUM regression tests ────────────────────────────────────
# Root cause: cc_ai_history.source was ENUM('db','ai','escalated') but the
# route was passing source='user' for user questions and ai_service can return
# source='error'. MySQL 8.0 strict mode silently rejected every INSERT so
# AI history was never stored.  v1.3 migration adds 'user' to the ENUM.
# The route was also fixed to skip saving error-source responses entirely.

VALID_AI_SOURCES = {'db', 'ai', 'escalated', 'user'}


class TestAiHistorySourceValues:
    """Guard that save_ai_message is only called with schema-valid source values."""

    def _capture_save_calls(self, monkeypatch, svc):
        saved = []

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.execute.side_effect = lambda sql, params=None: saved.append((sql, params))
            conn.cursor.return_value = cur
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        return saved

    def test_save_user_message_uses_valid_source(self, fake_db, monkeypatch):
        """save_ai_message with source='user' must pass a value in the ENUM."""
        import services.connect_service as svc
        saved = self._capture_save_calls(monkeypatch, svc)

        svc.save_ai_message(1, 'user', 'What events are today?', source='user')

        ai_inserts = [(sql, params) for sql, params in saved
                      if sql and 'cc_ai_history' in sql]
        assert ai_inserts, "Expected at least one INSERT into cc_ai_history"
        _, params = ai_inserts[0]
        source_value = params[3]  # 4th param = source
        assert source_value in VALID_AI_SOURCES, (
            f"source='{source_value}' is not in the cc_ai_history ENUM {VALID_AI_SOURCES}. "
            f"This causes MySQL strict-mode to silently drop the INSERT, "
            f"breaking AI history persistence."
        )

    def test_save_db_source_is_valid(self, fake_db, monkeypatch):
        import services.connect_service as svc
        saved = self._capture_save_calls(monkeypatch, svc)

        svc.save_ai_message(1, 'assistant', 'Here are the events...', source='db')

        ai_inserts = [(sql, params) for sql, params in saved
                      if sql and 'cc_ai_history' in sql]
        assert ai_inserts
        _, params = ai_inserts[0]
        assert params[3] in VALID_AI_SOURCES

    def test_save_ai_source_is_valid(self, fake_db, monkeypatch):
        import services.connect_service as svc
        saved = self._capture_save_calls(monkeypatch, svc)

        svc.save_ai_message(2, 'assistant', 'The answer is...', source='ai')

        ai_inserts = [(sql, params) for sql, params in saved
                      if sql and 'cc_ai_history' in sql]
        assert ai_inserts
        _, params = ai_inserts[0]
        assert params[3] in VALID_AI_SOURCES

    def test_error_source_is_not_passed_to_save(self, fake_db, monkeypatch):
        """The route must NOT call save_ai_message when the AI returns source='error'.
        Sending 'error' would be rejected by MySQL and silently corrupt history."""
        import routes.connect as connect_route
        import services.connect_service as svc_mod

        save_calls = []
        monkeypatch.setattr(svc_mod, 'save_ai_message',
                            lambda *a, **kw: save_calls.append(kw.get('source', a[3] if len(a) > 3 else None)))

        # Simulate an AI pipeline that returns source='error' (rate limited, etc.)
        monkeypatch.setattr(
            'routes.connect.ai_service.campus_connect_ai',
            lambda *a, **kw: {'answer': 'Rate limit hit', 'source': 'error',
                              'intent': 'general', 'escalate': False, 'confidence': 0}
        )
        monkeypatch.setattr(
            'routes.connect.connect_service.get_ai_history', lambda *a, **kw: []
        )
        from services.user_service import get_preferences as _gp
        monkeypatch.setattr('routes.connect.connect_service.get_ai_history', lambda *a, **kw: [])

        # Build a minimal Flask request context to test the route logic directly
        import importlib
        app_mod = importlib.import_module('app')
        app = app_mod.create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

        # Patch get_preferences inside the request context
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 5
                sess['role'] = 'student'
                sess['name'] = 'Test'
                sess['club_id'] = None

            # Patch user_service.get_preferences so the route doesn't need real DB
            import services.user_service as usr_svc
            monkeypatch.setattr(usr_svc, 'get_preferences', lambda uid: {'ai_response_style': 'concise'})
            monkeypatch.setattr(usr_svc, 'get_user_by_id', lambda uid: {'user_id': uid, 'name': 'Test'})
            monkeypatch.setattr(svc_mod, 'get_ai_history', lambda *a, **kw: [])

            resp = client.post('/connect/api/ai/ask',
                               json={'question': 'test question'},
                               content_type='application/json')

        # The route must NOT have called save_ai_message at all for error responses
        assert 'error' not in save_calls, (
            "save_ai_message was called with source='error'. "
            "This would corrupt AI history in MySQL strict mode."
        )


# ── escalate_to_coordinator: double-close regression ─────────────────────────

class TestEscalateToCoordinator:
    def test_no_double_close(self, fake_db, monkeypatch):
        """escalate_to_coordinator must close the connection exactly once.
        A duplicate conn.close() was present in the finally block — not a crash
        because close() is idempotent in mysql-connector, but it indicates
        sloppy resource management and can mask future errors."""
        import services.connect_service as svc

        close_count = 0

        def fake_get_db():
            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = None  # no coordinator found → returns False
            conn.cursor.return_value = cur

            nonlocal close_count

            def count_close():
                nonlocal close_count
                close_count += 1

            conn.close.side_effect = count_close
            return conn

        monkeypatch.setattr(svc, 'get_db_connection', fake_get_db)
        svc.escalate_to_coordinator(1, 'Alice', 'What events are on?')

        assert close_count == 1, (
            f"escalate_to_coordinator called conn.close() {close_count} times "
            f"(expected exactly 1). Duplicate close in finally block was found."
        )

