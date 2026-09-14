-- =============================================================================
-- CECRMS — Database Schema
-- Single source of truth for the complete database structure.
--
-- Fresh installation (from the project root):
--
--   mysql -u root -p < database/schema.sql          ← creates DB + all tables
--   mysql -u root -p cecrms < database/seed.sql     ← optional demo data
--
-- This file:
--   1. Creates the `cecrms` database if it does not exist.
--   2. Drops and recreates all tables — safe to re-run to reset the schema.
--   3. Includes every change from migrations v1.1 through v1.3, so fresh
--      installs never need to run the migration files.
--
-- Existing databases (upgrading from an older schema):
--   Run the migrations in order — see database/migrations/*.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS cecrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cecrms;

SET FOREIGN_KEY_CHECKS = 0;

-- ── Drop existing tables (reverse dependency order) ─────────────────────────
DROP TABLE IF EXISTS cc_ai_history;
DROP TABLE IF EXISTS cc_announcements;
DROP TABLE IF EXISTS cc_conversation_state;
DROP TABLE IF EXISTS cc_messages;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS membership_requests;
DROP TABLE IF EXISTS club_members;
DROP TABLE IF EXISTS user_activity;
DROP TABLE IF EXISTS activity_logs;
DROP TABLE IF EXISTS certificates;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS club_images;
DROP TABLE IF EXISTS event_images;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS venues;
DROP TABLE IF EXISTS clubs;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ─────────────────────────────────────────────────────────────────────────────
-- USERS
-- role: admin = system admin | club_admin = coordinator | student = regular user
-- club_id: set ONLY for club_admin rows to identify which club they coordinate.
--          Student club membership is tracked separately in club_members —
--          never use users.club_id to check whether a student belongs to a club.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin','club_admin','student') NOT NULL DEFAULT 'student',
  phone         VARCHAR(20),
  club_id       INT DEFAULT NULL,
  avatar_path   VARCHAR(255) DEFAULT NULL,
  preferences   JSON DEFAULT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CLUBS
-- coordinator_id: FK to the user currently coordinating this club
-- assigned_at/assigned_by: bookkeeping for the last coordinator assignment
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE clubs (
  club_id        INT AUTO_INCREMENT PRIMARY KEY,
  club_name      VARCHAR(150) NOT NULL,
  description    TEXT,
  coordinator_id INT DEFAULT NULL,
  assigned_at    TIMESTAMP NULL DEFAULT NULL,
  assigned_by    INT DEFAULT NULL,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  club_email     VARCHAR(255),
  FOREIGN KEY (coordinator_id) REFERENCES users(user_id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_by)    REFERENCES users(user_id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────────────────────────────────────
-- VENUES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE venues (
  venue_id   INT AUTO_INCREMENT PRIMARY KEY,
  venue_name VARCHAR(150) NOT NULL,
  capacity   INT DEFAULT NULL,
  location   VARCHAR(255),
  type       VARCHAR(100)
);


-- ─────────────────────────────────────────────────────────────────────────────
-- EVENTS
-- attendance_code/code_expires_at: coordinator-generated code, manual marking
-- attendance_otp/otp_generated_at: 6-digit self-submit OTP (expires 5 min)
-- category: used by the recommendation engine's "same category" boost
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE events (
  event_id          INT AUTO_INCREMENT PRIMARY KEY,
  club_id           INT NOT NULL,
  title             VARCHAR(255) NOT NULL,
  description       TEXT,
  event_lead        VARCHAR(150),
  contact_no        VARCHAR(30),
  venue_id          INT,
  date              DATE,
  start_time        TIME,
  end_time          TIME,
  poster            VARCHAR(255),
  registration_link VARCHAR(512),
  approved_status   ENUM('Pending','Approved','Rejected') DEFAULT 'Pending',
  category          VARCHAR(100) NULL DEFAULT NULL,
  attendance_code   VARCHAR(20)  NULL DEFAULT NULL,
  code_expires_at   DATETIME     NULL DEFAULT NULL,
  attendance_otp    VARCHAR(6)   NULL DEFAULT NULL,
  otp_generated_at  DATETIME     NULL DEFAULT NULL,
  created_by        INT,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (club_id)    REFERENCES clubs(club_id)   ON DELETE CASCADE,
  FOREIGN KEY (venue_id)   REFERENCES venues(venue_id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES users(user_id)   ON DELETE SET NULL,
  UNIQUE KEY ux_events_attendance_code (attendance_code)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- EVENT IMAGES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE event_images (
  img_id   INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  img_path VARCHAR(255) NOT NULL,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CLUB IMAGES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE club_images (
  img_id   INT AUTO_INCREMENT PRIMARY KEY,
  club_id  INT NOT NULL,
  img_path VARCHAR(255) NOT NULL,
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE
);


-- ─────────────────────────────────────────────────────────────────────────────
-- ATTENDANCE
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE attendance (
  attendance_id INT AUTO_INCREMENT PRIMARY KEY,
  event_id      INT NOT NULL,
  user_id       INT NOT NULL,
  scan_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  scan_by       INT DEFAULT NULL,
  UNIQUE KEY unique_attendance (event_id, user_id),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
  FOREIGN KEY (scan_by)  REFERENCES users(user_id)   ON DELETE SET NULL
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CERTIFICATES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE certificates (
  cert_id    INT AUTO_INCREMENT PRIMARY KEY,
  event_id   INT NOT NULL,
  user_id    INT NOT NULL,
  issue_date DATE,
  cert_path  VARCHAR(255),
  UNIQUE KEY unique_certificate (event_id, user_id),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ACTIVITY LOGS — admin/coordinator audit trail
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE activity_logs (
  log_id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  action      VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50),
  entity_id   INT,
  details     TEXT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_created (created_at),
  INDEX idx_user    (user_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- USER ACTIVITY — feeds the recommendation engine
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE user_activity (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  user_id          INT NOT NULL,
  event_id         INT NOT NULL,
  interaction_type ENUM('viewed','clicked','attended') NOT NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_view (user_id, event_id),
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CLUB MEMBERS — club membership roster (source of truth for "is X a member
-- of club Y", NOT users.club_id)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE club_members (
  member_id INT AUTO_INCREMENT PRIMARY KEY,
  club_id   INT NOT NULL,
  user_id   INT NOT NULL,
  position  ENUM('President','Vice President','Secretary','Treasurer',
                 'Coordinator','Volunteer','Member') NOT NULL DEFAULT 'Member',
  joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_member (club_id, user_id),
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- MEMBERSHIP REQUESTS — student "join club" request workflow
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE membership_requests (
  request_id INT AUTO_INCREMENT PRIMARY KEY,
  club_id    INT NOT NULL,
  user_id    INT NOT NULL,
  status     ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_request (club_id, user_id),
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- NOTIFICATIONS
-- type:      short tag used for icon/color selection in the UI (info/success/
--            danger/warning/cc_message/cc_announcement/cc_escalation/...)
-- event_key: optional dedup key; unique per (user_id, event_key) so the same
--            underlying event never creates two notification rows.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE notifications (
  notif_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  title      VARCHAR(255) NOT NULL,
  body       TEXT,
  link       VARCHAR(512),
  type       VARCHAR(50) NOT NULL DEFAULT 'info',
  event_key  VARCHAR(150) DEFAULT NULL,
  is_read    TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_user_unread (user_id, is_read),
  UNIQUE KEY ux_notif_dedup (user_id, event_key)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CAMPUS CONNECT — unified chat, announcements & AI assistant module
-- ─────────────────────────────────────────────────────────────────────────────

-- cc_messages: private 1:1 direct messages (student <-> coordinator <-> admin)
CREATE TABLE cc_messages (
  msg_id      INT AUTO_INCREMENT PRIMARY KEY,
  sender_id   INT NOT NULL,
  receiver_id INT NOT NULL,
  body        TEXT NOT NULL,
  is_read     TINYINT(1) NOT NULL DEFAULT 0,
  read_at     TIMESTAMP NULL DEFAULT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sender_id)   REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (receiver_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_cc_msg_sender   (sender_id),
  INDEX idx_cc_msg_receiver (receiver_id, is_read)
);

-- cc_conversation_state: per-user archive/hide flags (independent per side —
-- one participant archiving/deleting a conversation never affects the other)
CREATE TABLE cc_conversation_state (
  user_id     INT NOT NULL,
  other_id    INT NOT NULL,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  is_deleted  TINYINT(1) NOT NULL DEFAULT 0,
  updated_at  TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, other_id),
  FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (other_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- cc_announcements: coordinator (own club only) / admin (any target) broadcasts
CREATE TABLE cc_announcements (
  ann_id      INT AUTO_INCREMENT PRIMARY KEY,
  author_id   INT NOT NULL,
  target_type ENUM('everyone','students','coordinators','club','user') NOT NULL,
  target_id   INT DEFAULT NULL,
  title       VARCHAR(255) NOT NULL,
  body        TEXT NOT NULL,
  is_pinned   TINYINT(1) NOT NULL DEFAULT 0,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (author_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_cc_ann_target (target_type, target_id)
);

-- cc_ai_history: per-user AI Assistant conversation log (context + audit trail)
CREATE TABLE cc_ai_history (
  hist_id    INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  role       ENUM('user','assistant') NOT NULL,
  content    TEXT NOT NULL,
  source     ENUM('db','ai','escalated','user') DEFAULT 'ai',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_cc_ai_user (user_id)
);

SELECT 'CECRMS schema created successfully.' AS status;
