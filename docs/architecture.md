# CampusOps — Technical Architecture

## 1. System Overview

```
Browser (HTML / Vanilla JS / Tailwind CSS)
         |
         | HTTP (Flask dev server / Waitress in production)
         v
  Flask Application  (app.py — create_app factory)
         |
         | Blueprint routing — 16 blueprints registered at startup
         v
   routes/          <- HTTP endpoints: auth, parsing, RBAC decorators
         |
         | Function calls
         v
   services/        <- Business logic + all parameterised SQL
         |
         | mysql-connector-python (connection pool)
         v
   MySQL 8.0+       <- 17 tables, FK-constrained schema
```

AI Assistant sub-system:

```
User question (Campus Connect)
        |
        v
  Intent Detection     <- keyword/regex matching, zero API calls
        |
        +-- Structured intent (event/club/attendance/...) ------+
        |        |                                               |
        |        v                                               |
        |   DB-first answer  (confidence >= 0.8)            (confidence < 0.8)
        |        |                                               |
        |        v                                               v
        |   Return answer                             OpenRouter LLM API
        |                                             (google/gemini-flash-1.5)
        |                                                        |
        +-- General intent ----------------------------------> fallback
                                                                 |
                                                         In-process cache
                                                         (10 min TTL, 500 entries)
```

---

## 2. Application Layers

### routes/

Each file is a Flask Blueprint registered in `app.py`. Responsibilities:

- Parse and validate incoming HTTP requests
- Enforce authentication (`@login_required`) and authorisation (`@admin_required`, `@club_admin_required`)
- Call service functions — **no SQL here**
- Return rendered templates or JSON responses
- Handle flash messages and HTTP redirects

Blueprints are registered with URL prefixes:

| Blueprint | Prefix |
|---|---|
| auth | (root) |
| dashboard | / |
| clubs | /clubs |
| events | /events |
| venues | /venues |
| recommendations | /recommendations |
| attendance | /attendance |
| certificates | /certificates |
| search | /search |
| notifications | /notifications |
| admin | /admin |
| connect | /connect |
| profile | /profile |
| settings | /settings |
| calendar | /calendar |
| export | /export |

### services/

One file per domain area. Responsibilities:

- All business logic
- All SQL (100% parameterised — `%s` placeholders)
- Data transformation before returning to routes
- Cross-service calls where needed (e.g., `attendance_service` calls `certificate_service`)

**No HTTP-related code belongs here.**

### helpers/

Reusable utilities shared by multiple blueprints:

| File | Purpose |
|---|---|
| `auth_helpers.py` | Three RBAC decorators: `@login_required`, `@admin_required`, `@club_admin_required` |
| `pagination.py` | `paginate(total, page, per_page)` — returns clamped page, total_pages, offset |
| `upload_helpers.py` | `save_upload()`, `delete_upload()`, `build_gallery_zip()` — extension allowlist + 5 MB limit |
| `certificate_helpers.py` | `generate_certificate()` — Pillow-based dark-theme PNG certificate (1400×900) |

### templates/

Jinja2 HTML templates. Base template `layout.html` provides:
- Sidebar navigation (role-conditional links)
- CSRF token meta tag + auto-injection script (patches all `<form>` submits and `fetch()` calls)
- Dark theme CSS + CDN script tags (Tailwind, Lucide, Chart.js)
- Global context processor injects: `current_user`, `session`, `unread_count`, `cc_unread_count`

### static/

- `css/style.css` — monolithic dark design system (CSS custom properties, component classes, responsive rules)
- `uploads/` — user-uploaded club/event gallery images (gitignored, recreated at runtime)
- `certificates/` — auto-generated PNG certificates (gitignored, recreated at runtime)

### database/

| File | Purpose |
|---|---|
| `schema.sql` | Creates all 17 tables from scratch — the canonical source of truth for fresh installs |
| `seed.sql` | Demo data for development: 3 clubs, 6 users, venues, events, announcements |
| `reset_database.sql` | One-command DROP + SOURCE schema.sql + SOURCE seed.sql |
| `migrations/` | Incremental upgrades for databases that predate the current schema.sql |

### tests/

`conftest.py` provides:
- `FakeCursor` / `FakeConnection` — in-memory DB-API stubs; no real MySQL needed
- `fake_db` fixture — monkeypatches `get_db_connection` in every service module
- `app` + `client` fixtures — CSRF disabled for test client
- `login_as(client, role, user_id, ...)` helper
- `no_openrouter_calls` autouse fixture — deletes `OPENROUTER_API_KEY` and resets AI cache/rate-log before every test

---

## 3. Request Flow

A typical authenticated page request:

```
1. Browser sends GET /clubs/
2. Flask routes to clubs.list_clubs (Blueprint: clubs, prefix /clubs)
3. @login_required checks session['user_id'] — redirects to /login if absent
4. Route calls get_all_clubs(), count_all_clubs() in club_service.py
5. service opens a pooled MySQL connection, executes parameterised SELECT
6. service returns list[dict] to route
7. Route calls render_template('clubs/list.html', clubs=..., user=...)
8. Jinja2 renders HTML using layout.html as base
9. Flask returns HTTP 200 with HTML body
10. Browser renders the page
```

A POST action (e.g., send Campus Connect message):

```
1. Browser sends POST /connect/api/conversations/<id>/send
   with JSON body {"body": "..."} and X-CSRFToken header
2. Flask-WTF validates CSRF token — returns 400 if missing/invalid
3. @login_required validates session
4. Route calls connect_service.send_message(sender_id, receiver_id, body)
5. send_message() calls can_message() — checks RBAC rules server-side
6. Inserts into cc_messages, upserts cc_conversation_state
7. Calls create_notification_safe() for the receiver (deduplicated)
8. Route returns {"success": true, "msg_id": ...}
```

---

## 4. Authentication Flow

```
POST /login
    |
    v
get_user_by_email(email)    <- SELECT * FROM users WHERE email = %s
    |
    v
verify_password(user, pw)   <- werkzeug check_password_hash (scrypt)
    |
    v
session.clear()
session['user_id'] = user_id
session['role']    = role
session['club_id'] = club_id   <- None for students, club_id for coordinators
    |
    v
redirect to /  (dashboard)
```

Sessions use Flask's signed cookie store (HMAC with SECRET_KEY). Cookies are set with `HttpOnly=True` and `SameSite=Lax`. `SESSION_COOKIE_SECURE=true` should be set for HTTPS production.

---

## 5. Role-Based Access Control (RBAC)

Three roles stored in `users.role`:

| Role value | Label |
|---|---|
| `'student'` | Student |
| `'club_admin'` | Club Coordinator |
| `'admin'` | System Administrator |

### Decorator layer (routes/)

```python
@login_required       # any authenticated user
@admin_required       # role == 'admin' only
@club_admin_required  # role in ('club_admin', 'admin')
```

Non-matching roles are redirected to the dashboard with a flash message.

### Service layer (services/)

Services independently enforce business-rule permissions to prevent bypassing the UI:

- `connect_service.can_message(sender_id, receiver_id)` — student can only message coordinators; coordinator can only message their own club members; admin can message anyone; replies always allowed
- `connect_service.create_announcement(...)` — students cannot post; coordinators can only target their own club; admin can target any group
- `certificate_service` and `attendance_service` — coordinators can only mark attendance for their own club's events
- `clubs.py` route — `_can_manage_club(club_id)` returns True only if admin or the assigned coordinator of that specific club

---

## 6. Campus Connect Architecture

### Data model

```
cc_messages
  msg_id, sender_id, receiver_id, body, is_read, read_at, created_at

cc_conversation_state
  (user_id, other_id) PK
  is_archived, is_deleted
  — per-user flags; archiving by one participant does not affect the other

cc_announcements
  ann_id, author_id, target_type, target_id, title, body, is_pinned, created_at
  target_type: ENUM('everyone','students','coordinators','club','user')

cc_ai_history
  hist_id, user_id, role, content, source, created_at
  role: ENUM('user','assistant')
  source: ENUM('db','ai','escalated','user')
```

### get_inbox() query

Returns the latest message per conversation partner using a `ROW_NUMBER() OVER (PARTITION BY ...)` window function. Excludes conversations the user has soft-deleted. Requires MySQL 8.0+.

### Conversation access control (IDOR prevention)

Every API endpoint that loads a conversation verifies the viewer is a participant:

```python
# routes/connect.py — api_conversation_thread()
has_history = connect_service.count_conversation(me['user_id'], other_id) > 0
if not has_history and not connect_service.can_message(me['user_id'], other_id):
    return jsonify({'error': 'You are not allowed to message this user.'}), 403
```

Admin moderation uses a separate `get_all_conversations_admin()` endpoint protected by `@admin_required`.

### Notifications fan-out

When an announcement is created, `_fanout_announcement_notifications()` queries eligible recipients and calls `create_notification_safe()` for each. Deduplication uses an `event_key` like `cc_ann_<ann_id>_<user_id>` — MySQL's `INSERT IGNORE` on a `UNIQUE KEY (user_id, event_key)` prevents duplicates even if the fan-out runs more than once.

---

## 7. AI Architecture

### Pipeline (services/ai_service.py)

```python
def campus_connect_ai(question, user_id, history, response_style):
    1. check_rate_limit(user_id)   # 20 req/min in-process sliding window
    2. detect_intent(question)     # keyword/regex → one of 9 intents
    3. answer_from_db(intent, ...)  # structured SQL query
       if confidence >= 0.8:
           return db_answer
    4. build_messages([system_prompt, ...history[-6:], question])
    5. answer_from_openrouter(messages)  # HTTP POST to openrouter.ai
       - retries (2 attempts), 20s timeout
       - in-process cache (10 min TTL, 500 entries, FIFO eviction)
    6. determine escalation flag (low confidence + non-general intent)
    7. return {answer, source, intent, escalate, confidence}
```

### Intents (database-first)

| Intent | DB query |
|---|---|
| event | Upcoming, today, or recent events from `events` table |
| club | All clubs with coordinator and member count |
| attendance | User's attendance records |
| certificate | User's certificates |
| venue | All venues with capacity/location |
| coordinator | Clubs and their coordinator contacts |
| announcement | Recent announcements from cc_announcements |
| general | Falls through to OpenRouter |

### API key handling

The OpenRouter API key is read exclusively from the environment (`os.getenv('OPENROUTER_API_KEY', '')`). It is never hardcoded, never logged, and never included in any response or template. If absent, the AI assistant gracefully declines questions that need LLM fallback, while continuing to answer database-backed questions.

---

## 8. Database Architecture

### Table groups

**Identity and access**
- `users` — all user accounts (students, coordinators, admins); passwords stored as scrypt hashes
- `activity_logs` — action audit trail for admin/coordinator operations

**Clubs and membership**
- `clubs` — club definitions with coordinator FK
- `club_members` — roster (source of truth for membership — NOT `users.club_id`)
- `membership_requests` — join-request workflow
- `club_images` — uploaded gallery images

**Events and attendance**
- `events` — event records with OTP fields and venue FK
- `event_images` — gallery
- `attendance` — one row per student per event (UNIQUE)
- `certificates` — one row per student per event (UNIQUE)
- `user_activity` — interaction log feeding the recommendation engine

**Venues**
- `venues` — venue definitions

**Communication**
- `notifications` — in-app notification centre with dedup via `event_key`
- `cc_messages` — 1:1 direct messages
- `cc_conversation_state` — per-user archive/delete flags
- `cc_announcements` — coordinator and admin broadcasts
- `cc_ai_history` — AI conversation log per user

### Key design decisions

- `club_members` is the authoritative source for whether a student belongs to a club; `users.club_id` is only set for coordinators (indicates which club they coordinate)
- `notifications.event_key` has a `UNIQUE KEY (user_id, event_key)`, enabling `INSERT IGNORE` for safe idempotent notification creation
- `cc_ai_history.source` distinguishes database-first answers (`'db'`), LLM answers (`'ai'`), escalated answers (`'escalated'`), and user messages (`'user'`)

---

## 9. Security Architecture

### CSRF

Flask-WTF `CSRFProtect(app)` is applied globally in `create_app()`. This protects all POST/PUT/DELETE endpoints. A `<meta name="csrf-token">` tag is injected in `layout.html`, and a JavaScript snippet auto-patches all `<form>` submits and `fetch()` calls with an `X-CSRFToken` header. Standalone pages (`login.html`, `register.html`) include a hidden `csrf_token` input directly.

### Password security

Werkzeug's `generate_password_hash` uses scrypt by default in recent versions. Verification uses `check_password_hash` — timing-safe comparison.

### Session security

```python
SESSION_COOKIE_HTTPONLY = True    # not accessible to JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF resistance for cross-origin requests
SESSION_COOKIE_SECURE   = False   # set True in .env for HTTPS production
```

### IDOR prevention

Campus Connect conversation endpoints verify the requesting user is a participant before serving data. The check happens in `services/connect_service.py`, not only in the UI.

### Environment secrets

All secrets (SECRET_KEY, DB_PASSWORD, OPENROUTER_API_KEY) are read from environment variables via python-dotenv. `.env` is listed in `.gitignore` and must never be committed.

---

## 10. File and Module Responsibilities

| Module | Key public functions |
|---|---|
| `user_service` | get_user_by_id, get_user_by_email, create_user, verify_password, update_profile, update_password, get_preferences |
| `club_service` | get_all_clubs, get_club_by_id, create_club, update_club, set_club_coordinator, get_coordinator_directory |
| `event_service` | get_all_events, count_all_events, get_event_by_id, create_event, update_event, get_related_events |
| `attendance_service` | generate_otp, get_event_by_otp, submit_otp_self, mark_attendance, has_attended, get_student_attendance_history, analytics functions |
| `certificate_service` | get_user_certificates, issue_certificate, certificate_exists, search_certificates |
| `connect_service` | can_message, send_message, get_inbox, get_conversation, mark_messages_read, create_announcement, save_ai_message, get_ai_history, escalate_to_coordinator |
| `ai_service` | campus_connect_ai, detect_intent, answer_from_db, answer_from_openrouter, check_rate_limit |
| `notification_service` | create_notification_safe, get_user_notifications, count_unread, mark_all_read |
| `log_service` | log_action, get_recent_activity |
| `recommendation_service` | get_recommendations, log_view |
| `member_service` | get_club_members, add_member, remove_member, is_member, get_clubs_for_user |

---

## 11. Testing Architecture

### Structure

All tests live in `tests/`. The `conftest.py` provides shared infrastructure:

- **FakeConnection / FakeCursor** — in-memory DB-API 2.0 stubs. `fetchone()` returns `(0,)` for plain cursors (mimics COUNT aggregate) or `None` for dict cursors (mimics "not found"). `fetchall()` returns `[]`.
- **fake_db fixture** — monkeypatches `get_db_connection` in every service module individually (necessary because services use `from database import get_db_connection` which binds the local name at import time)
- **no_openrouter_calls autouse fixture** — ensures `OPENROUTER_API_KEY` is absent for every test body

### Test files

| File | What it tests |
|---|---|
| test_auth.py | Login/register/logout flow; CSRF on login and register |
| test_rbac_helpers.py | RBAC decorators for all three roles |
| test_dashboard.py | Dashboard renders for student, coordinator, and admin |
| test_attendance.py | OTP generation format, expiry, submission, certificate auto-issue |
| test_certificates.py | Certificate existence check, deduplication |
| test_notifications.py | create_notification_safe dedup; mark-all-read route |
| test_calendar.py | Month view, agenda view, month navigation, day-detail API |
| test_pagination.py | Edge cases (empty set, page clamping) |
| test_error_pages.py | 403, 404, 500 page rendering |
| test_export.py | Export page; all 6 datasets × 3 formats |
| test_search.py | Quick-search API, full results page |
| test_recommendations.py | Recommendations page; student-only RBAC |
| test_profile_settings.py | Profile view RBAC; password change; preferences save |
| test_ai_service.py | Intent detection; rate limiting; main pipeline |
| test_ai_service_regression.py | 48 pattern/pipeline/config regression tests |
| test_connect_service.py | SQL placeholder counts; ENUM source values; escalate double-close; RBAC |
| test_connect_routes.py | Campus Connect route handlers |
| test_connect_rbac.py | Messaging and announcement RBAC for all three roles |

Current result: **261 passed, 0 failures.**
