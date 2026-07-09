-- schema.sql — CECRMS Reference Schema (canonical, matches live DB)
-- This file is for reference only. To migrate an existing DB, use migrate.sql + migrate_coordinator_v2.sql.
-- To start fresh, run this file on an empty MySQL 8.0+ server.

CREATE DATABASE IF NOT EXISTS cecrms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cecrms;

-- ─────────────────────────────────────────────────────────────────────────────
-- USERS
-- role: admin = system admin | club_admin = coordinator | student = regular user
-- club_id: set for club_admin rows to identify which club they coordinate
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE users (
  user_id       INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin','club_admin','student') NOT NULL DEFAULT 'student',
  phone         VARCHAR(20),
  club_id       INT DEFAULT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CLUBS
-- coordinator_id: FK to the user currently coordinating this club
-- assigned_at:    timestamp when coordinator was last assigned
-- assigned_by:    FK to the admin who made the assignment
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
-- RESOURCES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE resources (
  resource_id    INT AUTO_INCREMENT PRIMARY KEY,
  resource_name  VARCHAR(150) NOT NULL,
  total_quantity INT DEFAULT 0,
  description    TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- EVENTS
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
  created_by        INT,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (club_id)    REFERENCES clubs(club_id)   ON DELETE CASCADE,
  FOREIGN KEY (venue_id)   REFERENCES venues(venue_id) ON DELETE SET NULL,
  FOREIGN KEY (created_by) REFERENCES users(user_id)   ON DELETE SET NULL
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
-- EVENT RESOURCES (pivot: which resources are used in which event)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE event_resources (
  event_id    INT NOT NULL,
  resource_id INT NOT NULL,
  quantity    INT NOT NULL DEFAULT 1,
  PRIMARY KEY (event_id, resource_id),
  FOREIGN KEY (event_id)    REFERENCES events(event_id)       ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- RESOURCE REQUESTS (Phase 4 approval workflow)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE resource_requests (
  request_id   INT AUTO_INCREMENT PRIMARY KEY,
  event_id     INT NOT NULL,
  club_id      INT NOT NULL,
  resource_id  INT NOT NULL,
  quantity     INT NOT NULL DEFAULT 1,
  requested_by INT NOT NULL,
  reviewed_by  INT DEFAULT NULL,
  status       ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id)     REFERENCES events(event_id)       ON DELETE CASCADE,
  FOREIGN KEY (club_id)      REFERENCES clubs(club_id)         ON DELETE CASCADE,
  FOREIGN KEY (resource_id)  REFERENCES resources(resource_id) ON DELETE CASCADE,
  FOREIGN KEY (requested_by) REFERENCES users(user_id)         ON DELETE CASCADE,
  FOREIGN KEY (reviewed_by)  REFERENCES users(user_id)         ON DELETE SET NULL
);

-- ─────────────────────────────────────────────────────────────────────────────
-- RESOURCE ALLOCATIONS (legacy; Phase 1 direct allocation)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE resource_allocations (
  alloc_id     INT AUTO_INCREMENT PRIMARY KEY,
  event_id     INT NOT NULL,
  resource_id  INT NOT NULL,
  quantity     INT NOT NULL DEFAULT 1,
  approved_by  INT,
  status       ENUM('Requested','Approved','Rejected') DEFAULT 'Requested',
  requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id)    REFERENCES events(event_id)       ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE,
  FOREIGN KEY (approved_by) REFERENCES users(user_id)         ON DELETE SET NULL
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
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ACTIVITY LOGS
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
-- USER ACTIVITY (for recommendation engine)
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
-- CLUB MEMBERS (club membership roster)
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
-- MEMBERSHIP REQUESTS
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
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE notifications (
  notif_id   INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  title      VARCHAR(255) NOT NULL,
  body       TEXT,
  link       VARCHAR(512),
  is_read    TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  INDEX idx_user_unread (user_id, is_read)
);
