# CECRMS — Campus Event & Club Resource Management System

A full-stack web application built with Python/Flask and MySQL for managing campus clubs, events, resources, attendance, and communication. Designed for three user roles: **Student**, **Club Coordinator**, and **Admin**.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [User Roles](#3-user-roles)
4. [Technology Stack](#4-technology-stack)
5. [Architecture Overview](#5-architecture-overview)
6. [Project Structure](#6-project-structure)
7. [Installation](#7-installation)
8. [Database Setup](#8-database-setup)
9. [Running the Application](#9-running-the-application)
10. [Test Suite](#10-test-suite)
11. [Database Migrations](#11-database-migrations)
12. [Campus Connect](#12-campus-connect)
13. [Security](#13-security)
14. [Screenshots](#14-screenshots)
15. [Demo Accounts](#15-demo-accounts)
16. [Known Limitations](#16-known-limitations)

---

## 1. Overview

CECRMS is a role-based campus management platform that lets students discover and attend events, coordinators manage their clubs and resources, and administrators oversee the entire campus ecosystem. It includes a **Campus Connect** module that provides 1:1 messaging, club announcements, admin broadcasts, and an AI-powered assistant that answers campus-related questions from the database and falls back to OpenRouter LLM when needed.

---

## 2. Key Features

| Module | Description |
|---|---|
| **Authentication** | Email/password login, registration, session management, CSRF protection |
| **Dashboard** | Role-specific stats, Chart.js analytics, upcoming events, activity feed |
| **Clubs** | Directory, image galleries, coordinator assignment, ZIP gallery download |
| **Club Membership** | Coordinator-managed roster, position titles, join-request workflow |
| **Events** | Create/edit/approve/reject, image galleries, venue conflict detection, registration links |
| **Attendance** | Coordinator generates a 6-digit OTP (5-minute expiry); students self-submit to mark attendance |
| **Certificates** | Auto-generated PNG certificate on attendance; public verification URL; personal list |
| **Resources** | Inventory management, approval-based request workflow, automatic release on event end |
| **Venues** | Venue directory with capacity/location, double-booking prevention |
| **Notifications** | In-app notification centre; deduplicated via event_key — one event = one notification |
| **Search** | Global Ctrl+K palette searching events, clubs, venues, people, announcements, AI history |
| **Recommendations** | Weighted engine based on attended clubs, event categories, and membership |
| **Calendar** | Month and agenda views; click-to-detail popover with attendance status |
| **Campus Connect** | Unified messaging, announcements, and AI Assistant (see section 12) |
| **Export** | Admin CSV / Excel / PDF export for students, attendance, events, resources, certificates |
| **Profile & Settings** | Avatar upload, password change, notification/AI/privacy preferences, activity timeline |

---

## 3. User Roles

### Student
- Browse events and club information
- Self-submit a 6-digit OTP to mark attendance at an event
- Self-generate PNG certificates after attending
- Message any club coordinator via Campus Connect
- Ask the AI Assistant campus questions
- View personal attendance history, certificates, and personalised recommendations

Cannot: create events, approve resources, manage clubs, send broadcasts, or access admin tools.

### Club Coordinator
- Manage their assigned club (edit details, upload gallery images)
- Create and manage events for their own club
- Generate OTPs for event attendance; mark attendance manually
- Manage club membership: add/remove members, assign position titles
- Request resources for events
- Reply to student messages; send club-scoped announcements
- Use the AI Assistant

Cannot: approve/reject resources, manage other clubs, assign coordinators, or send system-wide broadcasts.

### Admin
- Full access to clubs, events, venues, and resources
- Approve/reject events and resource requests
- Assign coordinators to clubs
- Send broadcasts to: everyone, all students, all coordinators, a specific club, or a specific user
- Moderate all Campus Connect conversations
- Export data in CSV / Excel / PDF
- View system-wide activity logs and analytics

---

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | Flask 2.3.3 |
| CSRF Protection | Flask-WTF 1.2.1 |
| Database | MySQL 8.0+ |
| MySQL Driver | mysql-connector-python 8.0.33 |
| Templating | Jinja2 (bundled with Flask) |
| CSS | Custom design system (static/css/style.css) + Tailwind CSS (CDN) |
| Icons | Lucide Icons (CDN) |
| Charts | Chart.js (CDN) |
| JavaScript | Vanilla JS (no frontend framework) |
| Image Generation | Pillow (certificate PNG generation) |
| Excel Export | openpyxl |
| PDF Export | reportlab |
| AI API | OpenRouter (optional) |
| Environment | python-dotenv |
| HTTP Client | requests (OpenRouter calls) |
| Testing | pytest 7.4.3 |

---

## 5. Architecture Overview

```
Browser
   |
Flask Application (app.py)
   | Blueprint routing
routes/         <- HTTP endpoints, auth checks, request parsing
   |
services/       <- Business logic, all SQL queries (parameterised)
   |
database.py     <- Pooled MySQL connection
   |
MySQL 8.0+
```

Helper layer (cross-cutting utilities):
- helpers/auth_helpers.py — @login_required, @admin_required, @club_admin_required
- helpers/pagination.py — page/offset calculation
- helpers/upload_helpers.py — file validation, save, delete, gallery ZIP
- helpers/certificate_helpers.py — Pillow-based certificate PNG generation

AI pipeline (Campus Connect):
```
User question
   |
Intent detection (keyword/regex — no API call)
   |
Database-first answer
   |--- Confidence >= 0.8 --> return answer
   |--- Confidence < 0.8  --> OpenRouter LLM fallback
                                  |
                              Cached response (10 min TTL)
```

---

## 6. Project Structure

```
DBMS Project2/
|-- app.py                   <- Flask application factory
|-- config.py                <- Environment-driven configuration
|-- database.py              <- MySQL connection pool
|-- requirements.txt         <- Python dependencies
|-- pytest.ini               <- Test configuration
|-- .env                     <- Local secrets (never committed)
|-- README.md
|
|-- routes/                  <- 17 Flask blueprints
|   |-- admin.py             <- Coordinator management
|   |-- attendance.py        <- OTP generation and submission
|   |-- auth.py              <- Login, register, logout
|   |-- calendar.py          <- Calendar view + day-detail API
|   |-- certificates.py      <- Certificate list, self-generate, verify
|   |-- clubs.py             <- Club CRUD, members, membership requests
|   |-- connect.py           <- Campus Connect (messages, announcements, AI)
|   |-- dashboard.py         <- Role-specific dashboard
|   |-- events.py            <- Event CRUD, gallery, detail
|   |-- export.py            <- CSV/Excel/PDF data exports (admin only)
|   |-- notifications.py     <- Notification centre
|   |-- profile.py           <- User profiles
|   |-- recommendations.py   <- Personalised event recommendations
|   |-- resources.py         <- Resource inventory and request workflow
|   |-- search.py            <- Full-text search + Ctrl+K API
|   |-- settings.py          <- Account settings and preferences
|   `-- venues.py            <- Venue management
|
|-- services/                <- Business logic and all SQL
|   |-- ai_service.py        <- AI pipeline (intent detection + OpenRouter)
|   |-- attendance_service.py
|   |-- certificate_service.py
|   |-- club_service.py
|   |-- connect_service.py   <- Campus Connect messages, announcements, AI history
|   |-- event_service.py
|   |-- log_service.py       <- Activity audit logging
|   |-- member_service.py
|   |-- membership_service.py
|   |-- notification_service.py
|   |-- recommendation_service.py
|   |-- resource_service.py
|   |-- user_service.py
|   `-- venue_service.py
|
|-- helpers/                 <- Shared utilities
|   |-- auth_helpers.py      <- RBAC decorators
|   |-- certificate_helpers.py  <- Pillow certificate generator
|   |-- pagination.py
|   `-- upload_helpers.py
|
|-- templates/               <- Jinja2 HTML templates (41 files)
|   |-- layout.html          <- Base template (sidebar, nav, CSRF injection)
|   |-- dashboard.html, login.html, register.html, ...
|   |-- admin/, attendance/, certificates/, clubs/
|   |-- components/          <- Reusable partials (event card, pagination)
|   |-- connect/             <- Campus Connect UI
|   |-- events/, resources/, venues/
|   `-- 403.html, 404.html, 500.html
|
|-- static/
|   |-- css/style.css        <- Complete dark-theme design system (1741 lines)
|   |-- uploads/             <- User-uploaded images (gitignored)
|   `-- certificates/        <- Generated certificate PNGs (gitignored)
|
|-- database/
|   |-- schema.sql           <- Complete database schema (single source of truth)
|   |-- seed.sql             <- Demo data (clubs, events, sample users)
|   |-- reset_database.sql   <- Drop + rebuild + seed convenience script
|   `-- migrations/          <- Incremental upgrades for existing databases
|       |-- v1.1_profile_settings.sql
|       |-- v1.2_campus_connect_schema.sql
|       `-- v1.3_ai_history_source_enum.sql
|
|-- tests/                   <- 189 automated tests (20 files)
|   |-- conftest.py          <- Shared fixtures (FakeDB, no real MySQL needed)
|   `-- test_*.py
|
`-- docs/
    |-- architecture.md      <- Technical architecture document
    `-- screenshots/         <- UI screenshots
```

---

## 7. Installation

Prerequisites: Python 3.11+, MySQL 8.0+

```powershell
# 1. Clone the repository
git clone <repository-url>
cd "DBMS Project2"

# 2. Create and activate virtual environment
python -m venv dbmsenv
.\dbmsenv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment — create .env with your local values:
# SECRET_KEY, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, OPENROUTER_API_KEY (optional)
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<any long random string>
DB_PASSWORD=<your MySQL root password>
DB_NAME=cecrms
```

OPENROUTER_API_KEY is optional. Without it, the AI Assistant answers database-backed questions but gracefully declines general questions that need an LLM.

---

## 8. Database Setup

### Fresh Installation

`schema.sql` creates the `cecrms` database and all tables in a single step — no manual `CREATE DATABASE` required.

```powershell
# Creates the database and all 20 tables
mysql -u root -p < database/schema.sql

# Optional: load demo data (clubs, events, users, announcements)
mysql -u root -p cecrms < database/seed.sql
```

One-command reset (drops the existing database and rebuilds from scratch):

```powershell
cd database
mysql -u root -p < reset_database.sql
```

> **Note:** `reset_database.sql` uses MySQL `SOURCE` with relative paths and must be run from inside the `database/` directory. Running it from the project root will fail.

### Upgrading an Existing Installation

Apply migrations in order:

```powershell
mysql -u root -p cecrms < database/migrations/v1.1_profile_settings.sql
mysql -u root -p cecrms < database/migrations/v1.2_campus_connect_schema.sql
mysql -u root -p cecrms < database/migrations/v1.3_ai_history_source_enum.sql
```

All migrations are idempotent — safe to run multiple times. See section 11 for details.

---

## 9. Running the Application

```powershell
python app.py
```

Open your browser at: http://127.0.0.1:5000

The application runs in debug mode when FLASK_DEBUG=true in .env (the default). For production use a WSGI server such as Gunicorn and set FLASK_DEBUG=false.

---

## 10. Test Suite

No real MySQL server is needed to run tests — database connections are mocked.

```powershell
python -m pytest
```

Verified result: 189 tests passed, 0 failures.

Tests cover: authentication, CSRF, RBAC decorators, dashboard rendering, attendance OTP, certificate dedup, resource approval notifications, notification dedup, calendar, pagination, Campus Connect (SQL placeholder correctness, ENUM validation, RBAC, IDOR protection, messaging, announcements, AI pipeline, AI history source), export, search, profile/settings, and error pages.

---

## 11. Database Migrations

Migrations in database/migrations/ upgrade existing databases. Fresh installations using schema.sql do not need them — all changes are already incorporated.

| Migration | What it adds | Who needs it |
|---|---|---|
| v1.1_profile_settings.sql | users.avatar_path and users.preferences columns | Databases built before profile/settings |
| v1.2_campus_connect_schema.sql | cc_conversation_state table; cc_messages.read_at column | Databases built before Campus Connect conversation state |
| v1.3_ai_history_source_enum.sql | Expands cc_ai_history.source ENUM to include 'user' | Databases where AI history inserts were silently failing |

---

## 12. Campus Connect

Campus Connect is the unified communication module accessible from the sidebar for all logged-in users.

### Messaging (1:1 Direct Messages)
- Students can initiate conversations with any club coordinator
- Coordinators can reply and start conversations with their own club members
- Admins can message anyone
- Read receipts and unread count badges
- Per-user archive and soft-delete (does not affect the other participant)

### Announcements and Broadcasts
- Coordinators send announcements to their own club members only
- Admins can target: everyone, all students, all coordinators, a specific club, or a specific user
- Pinned announcements float to the top
- Every announcement creates a deduplicated in-app notification

### AI Assistant
Questions are answered in two stages:
1. Database-first: events, clubs, attendance, resources, venues, coordinators — answered directly from MySQL (no LLM cost)
2. OpenRouter fallback: unstructured questions go to the configured model with retry, 20s timeout, and a 10-minute in-process response cache

AI conversation history persists in cc_ai_history across page refreshes and sessions.

### Access Control
- Users can only read their own conversations (IDOR protection enforced server-side)
- Coordinators can only send club announcements to their own club
- Admin moderation view shows all conversations
- All checks enforced in service layer, not only in the UI

---

## 13. Security

| Mechanism | Implementation |
|---|---|
| Password hashing | Werkzeug generate_password_hash / check_password_hash (scrypt) |
| CSRF | Flask-WTF CSRFProtect applied globally; token auto-injected into forms and fetch() calls |
| Session security | HttpOnly and SameSite=Lax cookies; SESSION_COOKIE_SECURE for HTTPS |
| Route RBAC | @login_required, @admin_required, @club_admin_required decorators |
| Service RBAC | Business logic independently validates permissions (e.g. can_message() in connect_service.py) |
| IDOR prevention | Conversation access verified server-side for every request |
| SQL injection | 100% parameterised queries; no string interpolation of user input |
| Secrets | All credentials from environment variables; .env is gitignored |
| File uploads | Extension allowlist + 5 MB size limit |

---

## 14. Screenshots

Screenshots are located in docs/screenshots/. The following are needed for the project submission:

| # | Screen | File |
|---|---|---|
| 1 | Login page | docs/screenshots/01_login.png |
| 2 | Student dashboard | docs/screenshots/02_student_dashboard.png |
| 3 | Clubs listing | docs/screenshots/03_clubs.png |
| 4 | Club detail + member list | docs/screenshots/04_club_detail.png |
| 5 | Events listing | docs/screenshots/05_events.png |
| 6 | Event detail | docs/screenshots/06_event_detail.png |
| 7 | Attendance OTP page | docs/screenshots/07_attendance_otp.png |
| 8 | Resource request form | docs/screenshots/08_resources.png |
| 9 | Certificates list | docs/screenshots/09_certificates.png |
| 10 | Campus Connect — inbox | docs/screenshots/10_cc_inbox.png |
| 11 | Campus Connect — conversation | docs/screenshots/11_cc_conversation.png |
| 12 | Campus Connect — AI Assistant | docs/screenshots/12_cc_ai.png |
| 13 | Campus Connect — announcements | docs/screenshots/13_cc_announcements.png |
| 14 | Coordinator dashboard | docs/screenshots/14_coordinator_dashboard.png |
| 15 | Admin dashboard | docs/screenshots/15_admin_dashboard.png |
| 16 | Admin — coordinator management | docs/screenshots/16_admin_coordinators.png |
| 17 | Calendar view | docs/screenshots/17_calendar.png |
| 18 | Search results | docs/screenshots/18_search.png |

All screenshots above require manual capture from the running application.

---

## 15. Demo Accounts

When the database is seeded with database/seed.sql, the following demo accounts are created:

| Role | Email |
|---|---|
| Admin | admin@cecrms.com |
| Coordinator (Robotics Club) | coord.robotics@cecrms.com |
| Coordinator (Music Club) | coord.music@cecrms.com |
| Student | asha@cecrms.com |
| Student | ravi@cecrms.com |
| Student | meera@cecrms.com |

Demo account passwords are documented in database/seed.sql. These are local development credentials only — never use them in any deployed environment.

---

## 16. Known Limitations

- **Manual attendance by code:** The attendance_code column exists in the schema, but no UI route generates such codes. The OTP system (6-digit numeric, 5-minute expiry) is the active attendance mechanism.
- **AI rate limiting:** The 20 requests/minute per-user limit uses an in-process dict and resets on Flask restart. A multi-worker deployment needs Redis.
- **No email notifications:** All notifications are in-app only; no SMTP integration is implemented.
- **File upload validation:** Extension-based only. Adding python-magic would provide stricter MIME-type verification.
