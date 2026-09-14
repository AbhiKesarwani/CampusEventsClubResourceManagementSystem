# CampusOps — Production Repository Discovery & Audit (Phase P1)

**Date**: September 14, 2026  
**Project**: CampusOps (University Club, Event & Resource Management System)  
**Stack**: Python 3 / Flask 2.3.3 + MySQL 8.0 + Jinja2 + Vanilla CSS / JS  
**Target Hosting**: Render (Web Service + Managed MySQL)  
**Current Test Baseline**: 261/261 tests passing (100%)  
**Phase Objective**: Discovery and audit only. **No files deleted, no code modified, no schemas changed.**

---

## 1. Root Directory Inventory

| File / Directory | Size / Type | Classification | Rationale |
|---|---|---|---|
| `.env` | 426 B (File) | `LOCAL ONLY` / `CONTAINS SECRETS` | Local environment variables & API keys. Ignored by Git. Never deploy to production. |
| `.git/` | Directory | `LOCAL ONLY` | Git version control metadata. |
| `.gitignore` | 2.5 KB (File) | `KEEP — deployment required` | Prevents secrets, virtual environments, caches, and large media from entering Git. |
| `.pytest_cache/` | Directory | `GENERATED` | Pytest execution and cache state. Reproducible. |
| `DBMS Project Video - Made with Clipchamp.mp4` | 86.8 MB (File) | `REMOVE CANDIDATE` / `LOCAL ONLY` | Large presentation video in repository root. Ignored by `*.mp4` in `.gitignore`, not tracked. Should be archived externally. |
| `README.md` | 29.6 KB (File) | `KEEP — documentation` | Project documentation, setup guide, credentials, and architectural summary. (Contains obsolete CECRMS / `/resources` references to be cleaned up). |
| `__pycache__/` | Directory | `GENERATED` | Compiled Python bytecode. Reproducible, ignored by Git. |
| `app.py` | 6.7 KB (File) | `KEEP — runtime required` | Application factory (`create_app`), blueprint registration, error handlers, Jinja context processors. |
| `config.py` | 3.3 KB (File) | `KEEP — runtime required` | Application configuration class (`Config`), environment variable defaults, session cookie security flags. |
| `database/` | Directory | `KEEP — database required` | Schema definitions, migration history, seed data. |
| `database.py` | 1.3 KB (File) | `KEEP — runtime required` | MySQL connection pool initialization (`_get_pool`) and `get_db_connection()`. |
| `dbmsenv/` | Directory | `LOCAL ONLY` | Local Python virtual environment. Ignored by Git. |
| `docs/` | Directory | `KEEP — documentation` | Architecture specifications, screenshots directory `.gitkeep`, phase reports. |
| `helpers/` | Directory | `KEEP — runtime required` | Utility functions: authentication RBAC, certificate generation, pagination, uploads. |
| `locustfile.py` | 7.3 KB (File) | `KEEP — test required` / `REVIEW` | Locust load-testing scenarios for student/admin concurrent traffic simulation. Not needed at runtime on Render. |
| `pytest.ini` | 80 B (File) | `KEEP — test required` | Pytest test configuration and directory discovery settings. |
| `requirements.txt` | 530 B (File) | `KEEP — deployment required` | Production and testing Python package dependencies. |
| `results/` | Directory (Untracked) | `GENERATED` | CSV metrics and statistics generated during previous Locust load tests. Should be added to `.gitignore`. |
| `routes/` | Directory | `KEEP — runtime required` | 16 Flask blueprint route modules. |
| `run_load_test.py` | 10.4 KB (File) | `REVIEW` | Standalone script for executing automated load testing with Waitress and Locust. Development utility. |
| `services/` | Directory | `KEEP — runtime required` | Core business logic layer (13 service modules). |
| `static/` | Directory | `KEEP — runtime required` | Stylesheet (`style.css`), hero illustration (`campus_students_illustration.svg`), uploads, certificates. |
| `templates/` | Directory | `KEEP — runtime required` | 39 Jinja2 HTML templates. |
| `tests/` | Directory | `KEEP — test required` | 27 automated test files (261 passing unit/regression tests). |
| `wsgi.py` | 1.6 KB (File) | `KEEP — deployment required` | Production WSGI entry point exposing `application = create_app()`. |

---

## 2. Python Code Inventory

### Runtime Required Modules (100% active)
- **Application Core**: `app.py`, `config.py`, `database.py`, `wsgi.py`.
- **Helpers (4 modules in `helpers/`)**:
  - `helpers/auth_helpers.py`: `@login_required`, `@admin_required`, `@club_admin_required`, role check helpers.
  - `helpers/certificate_helpers.py`: ReportLab PDF canvas drawing, UUID token generator, verification badge layout.
  - `helpers/pagination.py`: Pagination helper slicing collections and producing query strings.
  - `helpers/upload_helpers.py`: Image validation, Pillow resizing, file type whitelist, secure filename generation.
- **Routes (16 active blueprints in `routes/`)**:
  - `auth.py`: Login, registration, password hashing (scrypt), forgot password token flow.
  - `dashboard.py`: Role-scoped dashboards (Student, Coordinator, Admin).
  - `clubs.py`: Club directory, details, member list, membership requests.
  - `events.py`: Event directory, details, creation, photo gallery uploads, ZIP downloads.
  - `venues.py`: Campus venue CRUD, capacity checking, booking conflicts.
  - `recommendations.py`: Personalized event recommendations based on club memberships and categories.
  - `attendance.py`: 6-digit OTP generation, QR/code submission, attendance marking.
  - `certificates.py`: Certificate issuance, viewing, verification route (`/certificates/verify/<token>`).
  - `search.py`: Live quick search API (`/search/quick`) and full-text search results page.
  - `notifications.py`: In-app notification inbox, mark-all-read endpoint.
  - `admin.py`: Coordinator assignments, platform oversight, admin controls.
  - `connect.py`: Campus Connect messaging hub, AI assistant proxy, announcement feeds.
  - `profile.py`: User profile view, avatar updates, activity history.
  - `settings.py`: Password change, notification & AI preference persistence.
  - `calendar.py`: Month view, agenda view, day event details JSON API.
  - `export.py`: Excel (.xlsx) and CSV reporting for attendance, events, clubs.
- **Services (13 active services in `services/`)**:
  - `ai_service.py`: OpenRouter LLM integration, intent routing, prompt engineering, context extraction.
  - `attendance_service.py`: Attendance recording, OTP validation, attendance percentage calculation.
  - `certificate_service.py`: Certificate records creation, idempotent issuance, token lookups.
  - `club_service.py`: Club database queries, coordinator assignments, club metadata.
  - `connect_service.py`: Conversations, messages, read states, unread counters, announcement CRUD, AI history.
  - `event_service.py`: Event CRUD, status transitions (Pending/Approved/Rejected), gallery photo tracking.
  - `log_service.py`: Audit logging for admin and coordinator actions.
  - `member_service.py`: Club membership queries, position assignments (President/Secretary/Member).
  - `membership_service.py`: Student join requests, coordinator approvals/rejections.
  - `notification_service.py`: System notifications with `event_key` idempotency.
  - `recommendation_service.py`: Collaborative and rule-based recommendation algorithms.
  - `user_service.py`: User lookups, preferences JSON, avatar path updates.
  - `venue_service.py`: Venue availability, capacity validation, conflicts.

### Development & Load Testing Utilities (Non-Runtime)
- `locustfile.py`: Load test user behaviors (Student browsing, login, dashboard, events).
- `run_load_test.py`: Standalone orchestrator executing Waitress on a dynamic port and gathering Locust metrics.

### Dead / Obsolete Code Findings
- **Stale Bytecode in `__pycache__`**:
  - `routes/__pycache__/resources.cpython-312.pyc`
  - `routes/__pycache__/resources.cpython-313.pyc`
  - `routes/__pycache__/resources.cpython-314.pyc`
  - `services/__pycache__/resource_service.cpython-312.pyc`
  - `services/__pycache__/resource_service.cpython-313.pyc`
  - `services/__pycache__/resource_service.cpython-314.pyc`
  *Finding*: The corresponding `.py` source files were deleted in Phase 3, but their pre-compiled `.pyc` files remained in `__pycache__`.

---

## 3. Template Inventory

All 39 templates in `templates/` were audited against Flask route handlers and template inheritance:

| Category | Template Path | Status | Rendered By / Included In |
|---|---|---|---|
| **Base & Layout** | `templates/layout.html` | Active | Extended by all 36 page templates |
| **Components** | `templates/components/event_card.html` | Active | Included in `events/list.html`, `dashboard.html`, `recommendations.html` |
| **Components** | `templates/components/pagination.html` | Active | Included in list templates |
| **Errors** | `templates/403.html` | Active | `app.py:forbidden` |
| **Errors** | `templates/404.html` | Active | `app.py:not_found` |
| **Errors** | `templates/500.html` | Active | `app.py:server_error` |
| **Auth** | `templates/login.html` | Active | `routes/auth.py:login` |
| **Auth** | `templates/register.html` | Active | `routes/auth.py:register` |
| **Auth** | `templates/forgot_password.html` | Active | `routes/auth.py:forgot_password` |
| **Auth** | `templates/reset_password.html` | Active | `routes/auth.py:reset_password` |
| **Core** | `templates/dashboard.html` | Active | `routes/dashboard.py:index` |
| **Core** | `templates/calendar.html` | Active | `routes/calendar.py:calendar_view` |
| **Core** | `templates/notifications.html` | Active | `routes/notifications.py:index` |
| **Core** | `templates/profile.html` | Active | `routes/profile.py:view_profile` |
| **Core** | `templates/settings.html` | Active | `routes/settings.py:settings_page` |
| **Core** | `templates/search_results.html` | Active | `routes/search.py:full_search` |
| **Core** | `templates/recommendations.html` | Active | `routes/recommendations.py:recommendations_page` |
| **Core** | `templates/export.html` | Active | `routes/export.py:export_index` |
| **Campus Connect**| `templates/connect/index.html` | Active | `routes/connect.py:index` |
| **Admin** | `templates/admin/coordinators.html` | Active | `routes/admin.py:manage_coordinators` |
| **Attendance** | `templates/attendance/code.html` | Active | `routes/attendance.py:generate_code` |
| **Attendance** | `templates/attendance/mark.html` | Active | `routes/attendance.py:mark_attendance` |
| **Attendance** | `templates/attendance/my.html` | Active | `routes/attendance.py:my_attendance` |
| **Certificates** | `templates/certificates/list.html` | Active | `routes/certificates.py:certificates_list` |
| **Certificates** | `templates/certificates/verify.html` | Active | `routes/certificates.py:verify_certificate` |
| **Clubs** | `templates/clubs/list.html` | Active | `routes/clubs.py:list_clubs` |
| **Clubs** | `templates/clubs/detail.html` | Active | `routes/clubs.py:club_detail` |
| **Clubs** | `templates/clubs/create.html` | Active | `routes/clubs.py:create_club` |
| **Clubs** | `templates/clubs/edit.html` | Active | `routes/clubs.py:edit_club` |
| **Clubs** | `templates/clubs/members.html` | Active | `routes/clubs.py:club_members` |
| **Clubs** | `templates/clubs/membership_requests.html` | Active | `routes/clubs.py:membership_requests` |
| **Events** | `templates/events/list.html` | Active | `routes/events.py:list_events` |
| **Events** | `templates/events/detail.html` | Active | `routes/events.py:detail` |
| **Events** | `templates/events/create.html` | Active | `routes/events.py:create_event` |
| **Events** | `templates/events/edit.html` | Active | `routes/events.py:edit_event` |
| **Venues** | `templates/venues/list.html` | Active | `routes/venues.py:list_venues` |
| **Venues** | `templates/venues/detail.html` | Active | `routes/venues.py:venue_detail` |
| **Venues** | `templates/venues/create.html` | Active | `routes/venues.py:create_venue` |
| **Venues** | `templates/venues/edit.html` | Active | `routes/venues.py:edit_venue` |

- **Unused templates**: `0`
- **Duplicate templates**: `0`
- **Legacy / Resources templates**: `0` (Completely absent from `templates/`)

---

## 4. Static Asset Inventory

1. **CSS**:
   - `static/css/style.css` (80.3 KB, 2,621 lines): Global styling, design system tokens, responsive rules, card/badge variants, modal animations.
2. **Images / SVGs**:
   - `static/images/campus_students_illustration.svg`: Illustrated hero visual used on auth screens (`login.html`, `register.html`, `forgot_password.html`).
3. **Uploads (`static/uploads/`)**:
   - `.gitkeep` (Tracked, required for directory structure).
   - 47 image files (club logos, event banners, user avatars from local testing). Ignored by Git.
4. **Certificates (`static/certificates/`)**:
   - `.gitkeep` (Tracked, required for directory structure).
   - 3 generated PNG certificate previews from local testing. Ignored by Git.
5. **Icons & Fonts**:
   - Lucide Icons (`unpkg.com/lucide@latest`) and Bootstrap Icons (`cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3`) are loaded via CDN in `layout.html`.
   - Inter font family is loaded via Google Fonts CDN in `layout.html`.
   - No local webfonts or vendor JS bundles are stored in `static/`.

---

## 5. Test Inventory (27 Files, 261 Tests)

| Test File | Tests | Target Domain | Active Feature? | Redundant? | Recommendation |
|---|---|---|---|---|---|
| `test_ai_service.py` | 12 | Campus Connect AI prompt & intent routing | Yes | No | KEEP |
| `test_ai_service_regression.py` | 49 | AI regex intent matching edge cases | Yes | No | KEEP |
| `test_attendance.py` | 7 | Attendance codes, OTP, duplicate scan prevention | Yes | No | KEEP |
| `test_auth.py` | 16 | Login, registration, password hashing, sessions | Yes | No | KEEP |
| `test_calendar.py` | 7 | Calendar month/agenda views, day detail API | Yes | No | KEEP |
| `test_certificates.py` | 3 | Certificate issuance idempotency, role scoping | Yes | No | KEEP |
| `test_connect_rbac.py` | 13 | Campus Connect messaging & announcement RBAC | Yes | No | KEEP |
| `test_connect_routes.py` | 9 | Campus Connect endpoints, JSON responses | Yes | No | KEEP |
| `test_connect_service.py` | 27 | Connect DB queries, unread counts, source ENUM | Yes | No | KEEP |
| `test_dashboard.py` | 5 | Dashboard rendering across all 3 roles | Yes | No | KEEP |
| `test_error_pages.py` | 4 | 404, 403, 500 error page handling | Yes | No | KEEP |
| `test_event_photos.py` | 10 | Event photo gallery uploads, ZIP downloads, RBAC | Yes | No | KEEP |
| `test_export.py` | 5 | CSV, XLSX, PDF data export endpoints | Yes | No | KEEP |
| `test_notifications.py` | 5 | Notification creation, idempotency, mark-as-read | Yes | No | KEEP |
| `test_pagination.py` | 5 | Page calculation, boundary clamps, empty sets | Yes | No | KEEP |
| `test_profile_settings.py` | 8 | User profiles, password change, preferences | Yes | No | KEEP |
| `test_rbac_helpers.py` | 4 | Auth decorators (`@login_required`, etc.) | Yes | No | KEEP |
| `test_recommendations.py` | 3 | Event recommendation engine and route | Yes | No | KEEP |
| `test_search.py` | 5 | Quick search API and full search results page | Yes | No | KEEP |
| `test_phase3d.py` | 12 | Password reset flow, avatar fallback, event timeline | Yes | Historical Name | KEEP (propose rename to `test_auth_reset_and_ui.py`) |
| `test_phase3e.py` | 7 | SVG illustration, announcement targets, bubble CSS | Yes | Historical Name | KEEP (propose rename to `test_ui_elements.py`) |
| `test_phase3f.py` | 6 | Venue capacity dropdowns, sidebar CSS | Yes | Historical Name | KEEP (propose rename to `test_venue_capacity_ui.py`) |
| `test_phase3g.py` | 4 | Register page layout, card borders, labels | Yes | Historical Name | KEEP (propose rename to `test_layout_borders.py`) |
| `test_phase3h.py` | 1 | Auth split-column ratio matching | Yes | Historical Name | KEEP (propose merge into `test_layout_borders.py`) |
| `test_phase4.py` | 5 | Responsive layout, viewport tags, mobile drawer | Yes | Historical Name | KEEP (propose rename to `test_responsive_layout.py`) |
| `test_phase5.py` | 29 | WSGI, Waitress, DB pooling, CSRF, logging | Yes | Historical Name | KEEP (propose rename to `test_production_readiness.py`) |
| `conftest.py` | — | Test fixtures, test client, mock DB | Yes | No | KEEP |

- **Total passing tests**: **261 passed, 0 failed** in 30.65s.
- **Obsolete tests to remove**: **0**. Every test guards a living feature or security boundary.
- **Structural suggestion**: Phase-named files (`test_phase3d.py` through `test_phase5.py`) should be grouped and renamed by domain in a future phase.

---

## 6. Database Inventory

1. **`database/schema.sql`** (21.9 KB, 373 lines):
   - Single source of truth for creating the complete database.
   - Creates database `cecrms` with `utf8mb4` encoding.
   - Creates tables: `users`, `clubs`, `venues`, `resources` *(legacy)*, `events`, `event_images`, `club_images`, `event_resources` *(legacy)*, `resource_requests` *(legacy)*, `attendance`, `certificates`, `activity_logs`, `user_activity`, `club_members`, `membership_requests`, `notifications`, `cc_messages`, `cc_conversation_state`, `cc_announcements`, `cc_ai_history`.
   - *Legacy observation*: Contains `resources`, `event_resources`, and `resource_requests` tables even though the application no longer has a Resources module.
2. **`database/seed.sql`** (11.2 KB, 163 lines):
   - Sample seed data providing 6 demo accounts across admin, club coordinators, and students.
   - Inserts sample clubs, venues, events, attendance, certificates, notifications, announcements.
   - *Legacy observation*: Contains `INSERT INTO resources` (5 rows) and `INSERT INTO resource_requests` (1 row).
3. **`database/reset_database.sql`** (985 B):
   - Utility script executing `DROP DATABASE IF EXISTS cecrms; SOURCE schema.sql; SOURCE seed.sql;`.
4. **`database/migrations/`**:
   - `v1.1_profile_settings.sql`: Adds `avatar_path`, `preferences` JSON, `user_activity` table.
   - `v1.2_campus_connect_schema.sql`: Adds `cc_messages`, `cc_conversation_state`, `cc_announcements`, `cc_ai_history`.
   - `v1.3_ai_history_source_enum.sql`: Modifies `cc_ai_history.source` ENUM (`'user'`, `'db'`, `'ai'`).
   - *Note*: All migrations are already merged into `database/schema.sql`.

---

## 7. Dependency Inventory (`requirements.txt`)

| Package | Version Specifier | Category | Runtime / Test / Deploy | Purpose |
|---|---|---|---|---|
| `Flask` | `==2.3.3` | Web Framework | **Runtime Required** | Core WSGI application framework, routing, templating. |
| `Flask-WTF` | `==1.2.1` | Security / CSRF | **Runtime Required** | CSRF token validation and session security. |
| `mysql-connector-python` | `==8.0.33` | Database | **Runtime Required** | MySQL database driver and connection pooling. |
| `Pillow` | `==10.0.1` | Media Processing | **Runtime Required** | Avatar thumbnailing, event poster compression, image validation. |
| `python-dotenv` | `==1.0.0` | Configuration | **Runtime Required** | Sourcing environment variables from `.env`. |
| `requests` | `==2.31.0` | HTTP Client | **Runtime Required** | Outbound API requests to OpenRouter AI service. |
| `openpyxl` | `==3.1.2` | Data Export | **Runtime Required** | Generating Excel (.xlsx) reports in `routes/export.py`. |
| `reportlab` | `==4.0.7` | Document Generation | **Runtime Required** | PDF certificate generation in `services/certificate_service.py`. |
| `pytest` | `==7.4.3` | Testing | **Test Required** | Automated test suite runner (Not required in production container). |
| `waitress` | `>=3.0.0` | WSGI Server | **Deployment (Windows/Local)** | Multi-threaded production WSGI server. |
| `locust` | `>=2.20.0` | Load Testing | **Dev / Test Required** | Concurrency load-testing tool (Not required in production container). |

### Render Dependency Gaps
- **Missing WSGI Server for Linux**: Render natively runs Linux containers. While Waitress functions on Linux, `gunicorn>=21.2.0` is the standard Linux WSGI server for Render.
- **Separate dev/test dependencies**: `pytest` and `locust` are bundled in `requirements.txt`. For production, splitting into `requirements.txt` and `requirements-dev.txt` is standard practice.

---

## 8. Configuration & Security Findings

> [!WARNING]
> **Secret Handling Rule**: Secret values are strictly withheld.

1. **SECRET FOUND — `.env`**:
   - The `.env` file exists in the local workspace and contains sensitive production credentials (`OPENROUTER_API_KEY`, `SECRET_KEY`, `DB_PASSWORD`).
   - `.env` is properly listed in `.gitignore` and **is NOT tracked in Git**.
2. **Missing `.env.example`**:
   - The repository currently lacks an `.env.example` template file. Anyone deploying to Render must guess which environment variables are expected.
3. **Fallback Defaults in `config.py`**:
   - `SECRET_KEY = os.getenv('SECRET_KEY', 'devsecret_change_in_prod')`: If `SECRET_KEY` is omitted in Render, it falls back to an insecure default.
   - `DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'`: `DEBUG` defaults to `True` if `FLASK_DEBUG` is not explicitly set to `'false'`. In production on Render, `FLASK_DEBUG=false` must be mandatory.
   - `DB_HOST`: Defaults to `127.0.0.1`. In production, must be overridden with the managed cloud database host.
4. **Session Cookie Security**:
   - `SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'`: Must be set to `'true'` in Render environment variables since Render serves over HTTPS.

---

## 9. Legacy / Obsolete Feature Audit

### Removed Resources Module
- **Code & UI**: Fully cleaned up. No active routes, services, or templates reference Resources.
- **Database Schema**: `database/schema.sql` still contains `CREATE TABLE resources`, `CREATE TABLE event_resources`, and `CREATE TABLE resource_requests`.
- **Database Seed**: `database/seed.sql` still inserts 5 resources and 1 resource request.
- **CSS Comment**: `static/css/style.css` line 742 still contains `/* ── Resource/Request Cards ── */`.
- **Documentation**: `README.md` and `docs/architecture.md` still document `/resources` endpoints and the resource reservation workflow.

### Old Branding ("CECRMS" vs. "CampusOps")
- **Active UI**: All pages have been updated to **CampusOps**.
- **Database Name / Pool**: Defaults in `config.py` and `database.py` remain `cecrms` and `cecrms_pool`.
- **Seed User Emails**: Default demo accounts use the `@cecrms.com` domain.
- **Documentation**: `README.md` and `docs/architecture.md` are titled `CECRMS — Campus Event & Club Resource Management System`.
- **Certificates**: Default director signature in `helpers/certificate_helpers.py` references `"CECRMS Director"`.

---

## 10. Generated / Temporary File Audit

| File / Folder | Location | Type | Status | Recommendation |
|---|---|---|---|---|
| `results/` | Repository Root | Directory (12 CSV files, ~410 KB) | Untracked | Candidate for cleanup / add to `.gitignore`. |
| `DBMS Project Video - Made with Clipchamp.mp4` | Repository Root | Video (86.8 MB) | Ignored by Git (`*.mp4`) | Move out of project directory before deployment. |
| `.pytest_cache/` | Repository Root | Directory | Ignored by Git | Clean reproducible cache. |
| `__pycache__/` | Multiple directories | Python bytecode (.pyc) | Ignored by Git | Contains stale `.pyc` from deleted modules; can be purged with `find . -name "*.pyc" -delete`. |
| `static/uploads/` | `static/uploads/` | User uploaded images (47 files, ~15 MB) | Ignored by Git (except `.gitkeep`) | Local runtime assets. Render starts with empty folder. |
| `static/certificates/` | `static/certificates/` | Generated certificates (3 files) | Ignored by Git (except `.gitkeep`) | Local runtime assets. Render starts with empty folder. |
| `dbmsenv/` | Repository Root | Local virtual environment | Ignored by Git | Never commit or deploy. |

---

## 11. Git Audit

- **Current Branch**: `main` (ahead of `origin/main` by 1 commit).
- **Working Tree**: 21 modified files (UI polish and CSS enhancements from Phases 5–7).
- **Untracked Items**: Only `results/` (Locust test results).
- **Security Check**:
  - `.env` is **NOT tracked**.
  - No secret keys, passwords, or tokens are committed.
  - Virtual environments (`dbmsenv/`) and `.pytest_cache/` are **NOT tracked**.
  - Video file (`DBMS Project Video - Made with Clipchamp.mp4`) is **NOT tracked**.
- **`.gitignore` Coverage**:
  - Very comprehensive (Python caches, virtual environments, `.env`, OS files, logs, media, static uploads).
  - Missing entry: `results/` (should be added to `.gitignore`).

---

## 12. Render Deployment Requirements

Deploying CampusOps to Render as a Web Service requires:

1. **WSGI Entry Point**:
   - `wsgi.py` already exists with `application = create_app()`.
   - Render's native web service command should be:
     `gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 4 --threads 2` (or Waitress if keeping Waitress).
2. **Dependencies**:
   - Add `gunicorn>=21.2.0` to `requirements.txt`.
   - Consider separating `locust` and `pytest` into a development requirements file.
3. **Environment Variables on Render**:
   - `FLASK_ENV=production`
   - `FLASK_DEBUG=false`
   - `SECRET_KEY=<generate_secure_hex>`
   - `SESSION_COOKIE_SECURE=true`
   - `DB_HOST=<remote_mysql_host>`
   - `DB_PORT=<remote_mysql_port>`
   - `DB_USER=<remote_mysql_user>`
   - `DB_PASSWORD=<remote_mysql_password>`
   - `DB_NAME=<remote_mysql_database>`
   - `DB_POOL_SIZE=10`
   - `OPENROUTER_API_KEY=<key_for_ai_assistant>`
   - `OPENROUTER_MODEL=openai/gpt-4o-mini`
   - `PYTHON_VERSION=3.11.9` (or 3.12/3.10)
4. **Database Migration Strategy**:
   - Render does not provide local MySQL. A managed MySQL database (e.g. Aiven, PlanetScale, Railway, AWS RDS, or Render PostgreSQL with adaptation) must be provisioned.
   - Run `database/schema.sql` on the remote MySQL instance prior to launching the web service.
5. **Ephemeral Storage Handling**:
   - On Render standard web services, files stored on disk (`static/uploads/` and `static/certificates/`) do not persist across restarts or redeploys.
   - For a production deployment, either a Render Persistent Disk must be mounted to `static/uploads`, or a cloud storage provider (e.g. AWS S3 / Cloudinary) should be planned in a subsequent phase.
6. **Documentation**:
   - A `.env.example` file is required to guide environment configuration.
   - A `render.yaml` (Blueprint specification) would allow one-click deployment.

---

## 13. Proposed Deletion / Cleanup List (For Future Phases)

> [!NOTE]
> Per Phase P1 rules, **NOTHING has been deleted**. This list represents recommended cleanup targets for Phase P2.

1. **Delete / Move Out of Root**:
   - `DBMS Project Video - Made with Clipchamp.mp4` (86.8 MB large media file, not part of source code).
   - `results/` folder (12 local Locust load-test CSV reports).
2. **Purge Stale Bytecode**:
   - Remove `__pycache__` folders containing `.pyc` files of deleted modules (`routes/__pycache__/resources.*.pyc`, `services/__pycache__/resource_service.*.pyc`).
3. **Add to `.gitignore`**:
   - `results/`
   - `load_test_report.txt`
4. **Database Cleanup (Optional / Schema Refinement)**:
   - Remove deprecated tables from `database/schema.sql` (`resources`, `event_resources`, `resource_requests`).
   - Remove resource inserts from `database/seed.sql`.
5. **Documentation Cleanup**:
   - Update `README.md` and `docs/architecture.md` to remove references to `/resources` and update branding from CECRMS to CampusOps.

---

## 14. Proposed Test Cleanup List (For Future Phases)

> [!NOTE]
> Per Phase P1 rules, **NO tests have been deleted or renamed**.

1. **Consolidate Phase-Named Test Files**:
   - `test_phase3d.py` (12 tests) → Rename to `test_auth_features_and_timeline.py`
   - `test_phase3e.py` (7 tests) → Rename to `test_ui_badges_and_illustrations.py`
   - `test_phase3f.py` (6 tests) → Rename to `test_venue_capacity_and_sidebar.py`
   - `test_phase3g.py` (4 tests) + `test_phase3h.py` (1 test) → Consolidate into `test_auth_layout_and_borders.py`
   - `test_phase4.py` (5 tests) → Rename to `test_responsive_cross_device.py`
   - `test_phase5.py` (29 tests) → Rename to `test_production_readiness.py`
2. **Total Test Assertion Integrity**:
   - Keep all 261 test assertions completely intact.
   - No feature test should be removed.

---

## 15. Files That MUST NOT Be Deleted

The following files are mission-critical and must be preserved during all future cleanup and deployment phases:

1. **Application Core**: `app.py`, `config.py`, `database.py`, `wsgi.py`, `requirements.txt`.
2. **Helpers**: All 4 files in `helpers/` (`auth_helpers.py`, `certificate_helpers.py`, `pagination.py`, `upload_helpers.py`).
3. **Routes**: All 16 files in `routes/`.
4. **Services**: All 13 files in `services/`.
5. **Templates**: All 39 files in `templates/` (100% active).
6. **Static**: `static/css/style.css`, `static/images/campus_students_illustration.svg`, `static/uploads/.gitkeep`, `static/certificates/.gitkeep`.
7. **Database**: `database/schema.sql`, `database/seed.sql`.
8. **Tests**: All 27 test files and `conftest.py`.

---

## 16. Risks & Unknowns

1. **Remote MySQL Connectivity**:
   - Render does not host a native free-tier MySQL database (Render only provides PostgreSQL natively). A third-party managed MySQL (Aiven, PlanetScale, Clever Cloud, AWS RDS) or custom Docker service must be used.
   - SSL certificates for remote MySQL connection (`ssl_ca`, `ssl_verify_cert`) may be required by providers like Aiven.
2. **Ephemeral Uploads**:
   - User-uploaded club logos, event posters, and avatars in `static/uploads/` will disappear when the container restarts unless a Render Persistent Disk is attached.
3. **Dependency on C-Extensions**:
   - `reportlab` and `Pillow` require C libraries on Linux. On Render's native Python environment, wheels are available, but build times and wheel compatibility should be verified during initial staging build.
4. **Configuration Defaults**:
   - `DEBUG` defaulting to `True` if `FLASK_DEBUG` is unset presents a security risk if environment variables are not correctly configured on Render.
