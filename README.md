# CampusOps — Campus Event & Club Operations Management System

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=flat&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Tests](https://img.shields.io/badge/Tests-261%20Passed-brightgreen?style=flat&logo=pytest&logoColor=white)](pytest.ini)
[![License](https://img.shields.io/badge/License-Educational%20%2F%20MIT-blue?style=flat)](LICENSE)

A robust, enterprise-grade full-stack web application built with **Python/Flask** and **MySQL** for managing campus clubs, events, attendance tracking, and communications. CampusOps is purpose-built for three distinct user roles: **Student**, **Club Coordinator**, and **Administrator**.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [User Roles & Permissions](#3-user-roles--permissions)
4. [Technology Stack](#4-technology-stack)
5. [Architecture Overview](#5-architecture-overview)
6. [Project Structure](#6-project-structure)
7. [Installation & Setup](#7-installation--setup)
8. [Database Setup & Management](#8-database-setup--management)
9. [Running the Application](#9-running-the-application)
10. [Test Suite](#10-test-suite)
11. [Database Migrations](#11-database-migrations)
12. [Campus Connect & AI Assistant](#12-campus-connect--ai-assistant)
13. [Security Architecture](#13-security-architecture)
14. [Screenshots](#14-screenshots)
15. [Demo Accounts](#15-demo-accounts)
16. [Known Limitations](#16-known-limitations)

---

## 1. Overview

CampusOps centralizes fragmented campus student affairs into an integrated digital hub. Students discover upcoming events, join clubs, verify attendance via dynamic OTPs, and download authentic certificates. Club coordinators manage their rosters, submit event proposals, and coordinate club operations. Administrators oversee system approvals, review audit logs, and export analytics.

Additionally, CampusOps includes **Campus Connect** — a real-time messaging, club/campus announcement hub, and an intelligent AI Assistant with **multi-model fallback orchestration** via OpenRouter.

---

## 2. Key Features

| Module | Description |
|---|---|
| **Authentication & RBAC** | Secure registration, login, session control, role-based access decorators, and CSRF protection. |
| **Dynamic Dashboard** | Role-tailored dashboards with Chart.js analytics, quick action tiles, and real-time activity feeds. |
| **Clubs Management** | Club profiles, coordinator assignments, image galleries with batch ZIP downloads, and membership rosters. |
| **Club Membership** | Application workflow (join requests), position assignments, and member roster controls. |
| **Event Life Cycle** | Event creation, review/approval workflow, date/venue collision checks, and image galleries. |
| **Attendance via OTP** | Coordinator generates a 6-digit dynamic OTP (5-minute expiry); students self-verify to register attendance. |
| **Certificate Engine** | High-resolution PNG certificates dynamically rendered with Pillow, complete with unique verification identifiers. |
| **Venues** | Facility directory with capacities and locations; automated double-booking prevention. |
| **In-App Notifications** | Notification center with deduplication via `event_key` ensuring users receive single, idempotent alerts. |
| **Universal Search (Ctrl+K)** | Instant search across events, clubs, venues, contacts, announcements, and AI query history. |
| **Smart Recommendations** | Weighted algorithm suggesting events based on student club affiliations, attendance history, and categories. |
| **Interactive Calendar** | Month and agenda schedule views with click-to-view popovers and attendance statuses. |
| **Campus Connect** | Direct messaging (1:1), club announcements, campus-wide broadcasts, and an AI campus assistant. |
| **Data Export** | Admin reporting supporting CSV, formatted Excel (`.xlsx`), and styled PDF (`.pdf`) downloads. |
| **Profile & Preferences** | Custom avatar uploads, password management, notification toggles, and AI persona styling (concise vs. detailed). |

---

## 3. User Roles & Permissions

| Capability / Action | Student | Club Coordinator | Admin |
|---|:---:|:---:|:---:|
| Browse Events, Clubs, & Venues | ✅ | ✅ | ✅ |
| Submit Event Attendance OTP | ✅ | — | — |
| Download Certificates | ✅ | — | ✅ |
| Propose Events for Club | — | ✅ (Own Club) | ✅ (Any Club) |
| Approve / Reject Events | — | — | ✅ |
| Generate Attendance OTPs | — | ✅ (Own Club Events) | ✅ |
| Manage Club Roster & Positions | — | ✅ (Own Club) | ✅ |
| Direct Message Coordinators | ✅ | ✅ | ✅ |
| Send Club Announcements | — | ✅ (Own Club Members) | ✅ |
| Broadcast System-Wide Announcements | — | — | ✅ |
| Moderate All Conversations | — | — | ✅ |
| Export Data (CSV / XLSX / PDF) | — | — | ✅ |
| View System Activity Logs | — | — | ✅ |

---

## 4. Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Runtime & Language** | Python 3.11+ | High-performance Python backend |
| **Web Framework** | Flask 2.3.3 | Modular architecture using 16 Blueprints |
| **Security & CSRF** | Flask-WTF 1.2.1 | Global CSRF tokens on all state-changing endpoints |
| **Database** | MySQL 8.0+ | Relational schema with foreign keys, indexes, and ENUMs |
| **Database Connector** | mysql-connector-python 8.0.33 | Thread-safe connection pooling (`MySQLConnectionPool`) |
| **Templating** | Jinja2 | Component-driven HTML templates |
| **Design System** | Custom CSS + Tailwind CSS (CDN) | Modern dark-mode palette (`static/css/style.css`) |
| **Icons & Visuals** | Lucide Icons (CDN) | Unified SVG iconography |
| **Data Visualizations** | Chart.js (CDN) | Interactive analytics and event statistics |
| **Media & Certificates** | Pillow (PIL) 10.1+ | Server-side programmatic certificate PNG generation |
| **Spreadsheet Exports** | openpyxl 3.1.2 | Styled Excel export with custom branding |
| **Document Exports** | reportlab 4.0.7 | Clean PDF reports with auto-wrapping tables |
| **AI Integration** | OpenRouter REST API | Multi-model fallback (GPT-4o-mini, Gemini, Llama, Qwen) |
| **Testing** | pytest 7.4.3 | Mock-based unit & integration tests (261 tests) |
| **Package Management** | pip / uv | Fast, reliable dependency resolution |

---

## 5. Architecture Overview

```
                        [ Web Browser (Desktop / Mobile) ]
                                        │
                                  HTTP Requests
                                        ▼
                           ┌─────────────────────────┐
                           │    Flask App (app.py)   │
                           │   - CSRF Protection     │
                           │   - Session Validation  │
                           └────────────┬────────────┘
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                     ▼
        ┌─────────────────────────┐           ┌─────────────────────────┐
        │  routes/ (16 Blueprints)│           │  helpers/               │
        │  HTTP request parsing,  │◄─────────┤  - auth_helpers (RBAC)  │
        │  view routing, and RBAC │           │  - upload_helpers       │
        └────────────┬────────────┘           │  - pagination           │
                     ▼                        │  - certificate_helpers  │
        ┌─────────────────────────┐           └─────────────────────────┘
        │   services/ Layer       │
        │   Business logic and    │
        │   parameterized queries │
        └──────┬────────────┬─────┘
               │            │
               ▼            ▼
     ┌──────────────┐   ┌──────────────────────────────────────────────┐
     │  database.py │   │ services/ai_service.py                       │
     │  Pooled Pool │   │ 1. Regex Intent Classifier (Zero cost)       │
     └──────┬───────┘   │ 2. Parameterized DB queries (Exact answers)  │
            │           │ 3. OpenRouter Cascade (Models Fallback Array)│
            ▼           └──────────────────────────────────────────────┘
     ┌──────────────┐
     │  MySQL 8.0+  │
     │  Database    │
     └──────────────┘
```

---

## 6. Project Structure

```
CampusOps/
│
├── app.py                      # Flask application factory, error handlers, template filters
├── config.py                   # Environment-driven configuration loader
├── database.py                 # Thread-safe MySQL connection pool
├── requirements.txt            # Python package dependencies
├── pytest.ini                  # Pytest test execution configuration
├── .env.example                # Sample environment configuration template
├── .gitignore                  # Production-ready git ignore rules
├── README.md                   # System documentation
│
├── routes/                     # 16 Modular Flask blueprints
│   ├── admin.py                # Admin coordinator directory and club assignment
│   ├── attendance.py           # Dynamic 6-digit OTP generation and student self-marking
│   ├── auth.py                 # User authentication, registration, logout, and CSRF
│   ├── calendar.py             # Event schedule calendar view & day-detail JSON API
│   ├── certificates.py         # Personal certificates, generation, and public verification
│   ├── clubs.py                # Club CRUD, public directory, member rosters, gallery ZIP
│   ├── connect.py              # Campus Connect (1:1 messaging, announcements, AI chat)
│   ├── dashboard.py            # Dynamic role-specific landing dashboards
│   ├── events.py               # Event lifecycle (create, edit, approve, cancel, gallery)
│   ├── export.py               # System data reporting in CSV, Excel (.xlsx), and PDF
│   ├── notifications.py        # In-app notifications feed and mark-read controls
│   ├── profile.py              # User profiles, avatar uploads, and activity history
│   ├── recommendations.py      # Personalized event recommendation feed
│   ├── search.py               # Global search modal (Ctrl+K) and full results page
│   ├── settings.py             # Account settings, security, and AI preferences
│   └── venues.py               # Venue directory and booking capacity overview
│
├── services/                   # Business logic and SQL interaction layer
│   ├── ai_service.py           # Hybrid AI engine: intent classification + OpenRouter fallback
│   ├── attendance_service.py   # Attendance record checking, OTP generation & expiry logic
│   ├── certificate_service.py  # Certificate issuing and database binding
│   ├── club_service.py         # Club metadata, image gallery, and coordinator lookups
│   ├── connect_service.py      # DMs, threads, announcements, and AI chat history
│   ├── event_service.py        # Event queries, status transitions, and collision checking
│   ├── log_service.py          # Centralized audit logging for system actions
│   ├── member_service.py       # Roster queries and membership position assignments
│   ├── membership_service.py   # Join requests, approvals, and cancellations
│   ├── notification_service.py # In-app notification creation with event_key deduplication
│   ├── recommendation_service.py # Multi-factor scoring for tailored event suggestions
│   ├── user_service.py         # User credentials, password hashing, and profile settings
│   └── venue_service.py        # Venue capacity and conflict prevention queries
│
├── helpers/                    # Shared utilities
│   ├── auth_helpers.py         # Role-based access decorators (@login_required, @admin_required)
│   ├── certificate_helpers.py  # Pillow image composer for high-res certificates
│   ├── pagination.py           # Reusable pagination math and bounds checking
│   └── upload_helpers.py       # Secure filename validation, upload storage, and ZIP bundling
│
├── templates/                  # Jinja2 templates with dark-mode aesthetic
│   ├── layout.html             # Base layout containing sidebar, header, and CSRF setup
│   ├── dashboard.html          # Dynamic multi-role dashboard
│   ├── login.html, register.html
│   ├── 403.html, 404.html, 500.html # Themed error handling pages
│   ├── admin/, attendance/, certificates/, clubs/
│   ├── components/             # Reusable UI partials (event cards, pagination)
│   ├── connect/                # Campus Connect messenger and AI chat interface
│   └── events/, venues/, profile.html, settings.html, export.html, calendar.html
│
├── database/                   # Database schemas, seeds, and migrations
│   ├── schema.sql              # Clean complete schema definition (17 tables)
│   ├── seed.sql                # Rich demo dataset (clubs, users, events, venues, announcements)
│   ├── reset_database.sql      # Database rebuild and seed utility script
│   └── migrations/             # Idempotent incremental migration scripts
│       ├── v1.1_profile_settings.sql
│       ├── v1.2_campus_connect_schema.sql
│       └── v1.3_ai_history_source_enum.sql
│
├── tests/                      # Automated test suite (261 tests, 100% pass)
│   ├── conftest.py             # Shared fixtures and FakeDB mock layer (runs without MySQL)
│   └── test_*.py               # 27 comprehensive test suites
│
├── docs/                       # Technical documentation and assets
│   ├── architecture.md         # Deep-dive architecture design documentation
│   └── screenshots/            # Visual walkthrough documentation
│
└── static/                     # Static client assets
    ├── css/style.css           # Modern design system and CSS styling
    ├── uploads/                # User uploaded club/event/avatar media (.gitignored)
    └── certificates/           # Generated certificate images (.gitignored)
```

---

## 7. Installation & Setup

### Prerequisites

- **Python**: Version 3.11 or higher
- **MySQL**: Version 8.0 or higher
- **Git**: Installed on your system
- Optional: `uv` package manager for fast execution

### Step 1: Clone the Repository

```powershell
git clone https://github.com/AbhiKesarwani/CampusEventsClubResourceManagementSystem.git
cd CampusEventsClubResourceManagementSystem
```

### Step 2: Set Up Virtual Environment

**Using standard Python `venv`:**
```powershell
python -m venv dbmsenv
.\dbmsenv\Scripts\Activate.ps1
```

**Or using `uv`:**
```powershell
uv venv dbmsenv
.\dbmsenv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory:

```env
# Flask Core
SECRET_KEY=your_super_secret_random_key_here
FLASK_DEBUG=true
SESSION_COOKIE_SECURE=false

# MySQL Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_root_password
DB_NAME=cecrms
DB_POOL_SIZE=5
DB_POOL_NAME=cecrms_pool

# File Uploads & Certificates
UPLOAD_FOLDER=static/uploads
MAX_UPLOAD_BYTES=5242880
CERT_FOLDER=static/certificates

# AI Campus Assistant (Optional - OpenRouter)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_FALLBACK_MODELS=google/gemini-2.0-flash-001,meta-llama/llama-3.3-70b-instruct,qwen/qwen-2.5-72b-instruct
OPENROUTER_TIMEOUT=20
```

> **Note:** `OPENROUTER_API_KEY` is optional. Without it, the AI Assistant answers all campus, club, event, and coordinator queries directly from the MySQL database, gracefully notifying users for general chit-chat.

---

## 8. Database Setup & Management

### Fresh Installation

`schema.sql` creates the `cecrms` database along with all 17 normalized tables:

```powershell
# 1. Create database schema
mysql -u root -p < database/schema.sql

# 2. Populate demo seed data (users, clubs, venues, events, announcements)
mysql -u root -p cecrms < database/seed.sql
```

### One-Command Reset

To drop the existing database and rebuild from scratch with seed data:

```powershell
cd database
mysql -u root -p < reset_database.sql
cd ..
```

> **Important:** `reset_database.sql` relies on relative `SOURCE` directives and must be executed from inside the `database/` directory.

### Incremental Migrations

For existing databases, apply incremental migrations in order:

```powershell
mysql -u root -p cecrms < database/migrations/v1.1_profile_settings.sql
mysql -u root -p cecrms < database/migrations/v1.2_campus_connect_schema.sql
mysql -u root -p cecrms < database/migrations/v1.3_ai_history_source_enum.sql
```

---

## 9. Running the Application

Ensure your virtual environment is active:

```powershell
python app.py
```

*Or run with `uv`:*
```powershell
uv run python app.py
```

Access the application in your browser:
👉 **`http://127.0.0.1:5000`**

---

## 10. Test Suite

The test suite runs **100% offline** without needing an active MySQL server. Tests leverage a high-speed `FakeDB` mock cursor framework that simulates query results and validates parameter binding.

Run all tests via pytest:

```powershell
python -m pytest
```

*Or via `uv`:*
```powershell
uv run pytest
```

### Test Coverage Highlights

```text
============================== test session starts ==============================
collected 261 items

27 comprehensive test suites covering auth, RBAC, events, clubs, venues,
attendance, certificates, notifications, Campus Connect, and admin workflows.

====================== 261 passed, 0 failures in ~27s ===========================
```

Key test categories:
- **Authentication & CSRF**: Session management, login failures, registration validations, and token injection.
- **Role-Based Access**: Multi-role verification preventing unauthorized student actions and IDOR vulnerabilities.
- **Attendance & OTP**: Expiration math, code format, duplicate prevention, and automated certificate issuing.
- **Campus Connect**: Conversation threading, unread counter badges, permission boundaries, and audit logging.
- **AI Engine & Resilience**: Intent recognition, zero-cost DB answers, multi-model fallback cascade, and timeout protections.
- **Data Exports**: Structural accuracy of CSV, openpyxl XLSX, and ReportLab PDF generated binaries.

---

## 11. Database Migrations

| Migration Script | Functionality | Target Databases |
|---|---|---|
| `v1.1_profile_settings.sql` | Adds `users.avatar_path` and `users.preferences` JSON columns. | Databases created prior to Profile/Settings update. |
| `v1.2_campus_connect_schema.sql` | Creates `cc_conversation_state` and adds `cc_messages.read_at`. | Databases initialized before messaging read-tracking. |
| `v1.3_ai_history_source_enum.sql` | Expands `cc_ai_history.source` ENUM to explicitly include `'user'`. | Databases where AI conversation logging was failing. |

*All migration scripts are idempotent and safe to apply against live databases.*

---

## 12. Campus Connect & AI Assistant

Campus Connect is the integrated real-time communication platform in CampusOps:

```
                                  ┌────────────────────────┐
                                  │     User Question      │
                                  └───────────┬────────────┘
                                              ▼
                                 [ Regex Intent Detection ]
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │ High Confidence Intent                        │ Unstructured / General
                      ▼                                               ▼
      ┌───────────────────────────────┐               ┌───────────────────────────────┐
      │ Parameterized Database Lookup │               │ OpenRouter Multi-Model Engine │
      │ - Upcoming events & venues    │               │  1. Primary Model             │
      │ - Club details & coordinators │               │  2. Configured Fallback Array │
      │ - Attendance & venues         │               │  3. Built-in Reliable Models  │
      └───────────────┬───────────────┘               └───────────────┬───────────────┘
                      │ Answer Found                                  │ Response Generated
                      └───────────────────────┬───────────────────────┘
                                              ▼
                                 ┌────────────────────────┐
                                 │ In-Memory Cache Entry  │
                                 │ (10-minute TTL)        │
                                 └────────────┬───────────┘
                                              ▼
                                 ┌────────────────────────┐
                                 │ Response to User + DB  │
                                 │ Conversation Logged    │
                                 └────────────────────────┘
```

### Multi-Model Fallback Cascade
If the configured primary model (`OPENROUTER_MODEL`) is unavailable or encounters rate limits (HTTP 429), the AI engine automatically falls back through `OPENROUTER_FALLBACK_MODELS`, testing up to 3 prioritized candidates in OpenRouter's native fallback array before gracefully handling failures.

### Real-Time Direct Messaging (DMs)
- Students can initiate direct conversations with club coordinators.
- Coordinators can correspond with their club members.
- Administrators can message any member across campus and review moderation queues.
- Read receipts, unread counter badges, and per-user archiving/soft-deletion.

---

## 13. Security Architecture

- **SQL Injection Immunization**: 100% of database queries utilize parameterized SQL with explicit parameter tuples. Zero string concatenation.
- **CSRF Defense**: Global `Flask-WTF` protection verifying tokens on all POST/PUT/DELETE requests, including asynchronous JavaScript `fetch()` calls.
- **Password Security**: Scrypt-based hashing via `werkzeug.security.generate_password_hash` and `check_password_hash`.
- **IDOR Safeguards**: Conversational, profile, and administrative endpoints rigorously verify session ownership on the server side.
- **Upload Hardening**: File uploads are restricted to an extension whitelist (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`) and strictly capped at 5 MB.
- **Cookie Hardening**: `HttpOnly` and `SameSite=Lax` cookies prevent script extraction; configurable HTTPS-only enforcement via `SESSION_COOKIE_SECURE`.

---

## 14. Screenshots

Reference mockups and application captures located in `docs/screenshots/`:

| # | Screen | Path |
|---|---|---|
| 01 | Authentication & Login | `docs/screenshots/01_login.png` |
| 02 | Student Dashboard | `docs/screenshots/02_student_dashboard.png` |
| 03 | Clubs Directory | `docs/screenshots/03_clubs.png` |
| 04 | Club Profile & Roster | `docs/screenshots/04_club_detail.png` |
| 05 | Events Directory & Filters | `docs/screenshots/05_events.png` |
| 06 | Event Details & Gallery | `docs/screenshots/06_event_detail.png` |
| 07 | Attendance OTP Generator & Verification | `docs/screenshots/07_attendance_otp.png` |
| 08 | Certificate Generation & Verification | `docs/screenshots/09_certificates.png` |
| 09 | Campus Connect — Message Threads | `docs/screenshots/10_cc_inbox.png` |
| 10 | Campus Connect — Conversation View | `docs/screenshots/11_cc_conversation.png` |
| 11 | Campus Connect — AI Assistant | `docs/screenshots/12_cc_ai.png` |
| 12 | Campus Connect — Announcements | `docs/screenshots/13_cc_announcements.png` |
| 13 | Coordinator Dashboard | `docs/screenshots/14_coordinator_dashboard.png` |
| 14 | Administrator Dashboard | `docs/screenshots/15_admin_dashboard.png` |
| 15 | Admin Coordinator Management | `docs/screenshots/16_admin_coordinators.png` |
| 16 | Schedule & Calendar View | `docs/screenshots/17_calendar.png` |
| 17 | Quick Search Modal (Ctrl+K) | `docs/screenshots/18_search.png` |

---

## 15. Demo Accounts

When initialized with `database/seed.sql`, the following demo accounts are available:

| Role | Email Address | Sample Credentials |
|---|---|---|
| **Administrator** | `admin@cecrms.com` | Documented in `database/seed.sql` |
| **Coordinator (Robotics Club)** | `coord.robotics@cecrms.com` | Documented in `database/seed.sql` |
| **Coordinator (Music Club)** | `coord.music@cecrms.com` | Documented in `database/seed.sql` |
| **Student** | `asha@cecrms.com` | Documented in `database/seed.sql` |
| **Student** | `ravi@cecrms.com` | Documented in `database/seed.sql` |
| **Student** | `meera@cecrms.com` | Documented in `database/seed.sql` |

> *Notice: These credentials are intended strictly for local development and demonstration purposes.*

---

## 16. Known Limitations

- **Rate Limiting Persistence**: AI assistant rate limits operate on an in-memory sliding window. Multi-worker deployments should adopt Redis.
- **In-App Notifications Only**: Notifications are currently in-app only; external email/SMS dispatch via SMTP/Twilio can be integrated as future extensions.
- **File Validation**: Image verification relies on extension and size validation. Adding `python-magic` would provide deeper binary MIME checking.
