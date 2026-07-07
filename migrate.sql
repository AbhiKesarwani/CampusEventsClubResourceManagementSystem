-- =============================================================
-- CECRMS Safe Migration Script
-- Run this on your EXISTING cecrms database.
-- Fully idempotent — safe to run multiple times.
-- Compatible with MySQL 8.0+
-- =============================================================

USE cecrms;

-- -------------------------------------------------------------
-- STEP 1: Remap old role values to new 3-role system
-- -------------------------------------------------------------
UPDATE users SET role = 'admin'
  WHERE role IN ('Coordinator') AND role != 'admin';

UPDATE users SET role = 'club_admin'
  WHERE role IN ('Co-Coordinator','Co-Coordinator-Ops','Co-Coordinator-PR','Co-Coordinator-Finance')
    AND role != 'club_admin';

UPDATE users SET role = 'student'
  WHERE (role = 'Student' OR role IS NULL) AND role != 'student';

-- Safely alter enum (idempotent — re-run safe)
ALTER TABLE users MODIFY COLUMN role ENUM('admin','club_admin','student') NOT NULL DEFAULT 'student';

-- -------------------------------------------------------------
-- STEP 2: Fix resources table column names if old schema
-- Safe: uses dynamic SQL conditioned on information_schema
-- -------------------------------------------------------------
SET @col_name_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resources' AND COLUMN_NAME = 'name'
);
SET @sql = IF(@col_name_exists > 0,
  'ALTER TABLE resources CHANGE COLUMN `name` `resource_name` VARCHAR(150) NOT NULL',
  'SELECT 1');
PREPARE _stmt FROM @sql; EXECUTE _stmt; DEALLOCATE PREPARE _stmt;

SET @col_stock_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resources' AND COLUMN_NAME = 'stock'
);
SET @sql2 = IF(@col_stock_exists > 0,
  'ALTER TABLE resources CHANGE COLUMN `stock` `total_quantity` INT DEFAULT 0',
  'SELECT 1');
PREPARE _stmt2 FROM @sql2; EXECUTE _stmt2; DEALLOCATE PREPARE _stmt2;

-- -------------------------------------------------------------
-- STEP 3: Add description column to resources (if absent)
-- -------------------------------------------------------------
SET @desc_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resources' AND COLUMN_NAME = 'description'
);
SET @sql3 = IF(@desc_exists = 0,
  'ALTER TABLE resources ADD COLUMN description TEXT',
  'SELECT 1');
PREPARE _stmt3 FROM @sql3; EXECUTE _stmt3; DEALLOCATE PREPARE _stmt3;

-- -------------------------------------------------------------
-- STEP 4: Add location + type columns to venues (if absent)
-- -------------------------------------------------------------
SET @loc_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'location'
);
SET @sql4 = IF(@loc_exists = 0,
  'ALTER TABLE venues ADD COLUMN location VARCHAR(255)',
  'SELECT 1');
PREPARE _stmt4 FROM @sql4; EXECUTE _stmt4; DEALLOCATE PREPARE _stmt4;

SET @type_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'venues' AND COLUMN_NAME = 'type'
);
SET @sql5 = IF(@type_exists = 0,
  'ALTER TABLE venues ADD COLUMN type VARCHAR(100)',
  'SELECT 1');
PREPARE _stmt5 FROM @sql5; EXECUTE _stmt5; DEALLOCATE PREPARE _stmt5;

-- -------------------------------------------------------------
-- STEP 5: Add registration_link column to events (if absent)
-- -------------------------------------------------------------
SET @reglink_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events' AND COLUMN_NAME = 'registration_link'
);
SET @sql6 = IF(@reglink_exists = 0,
  'ALTER TABLE events ADD COLUMN registration_link VARCHAR(512)',
  'SELECT 1');
PREPARE _stmt6 FROM @sql6; EXECUTE _stmt6; DEALLOCATE PREPARE _stmt6;

-- -------------------------------------------------------------
-- STEP 6: event_images table (if not present)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_images (
  img_id    INT AUTO_INCREMENT PRIMARY KEY,
  event_id  INT NOT NULL,
  img_path  VARCHAR(255) NOT NULL,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- STEP 7: club_images table (if not present)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS club_images (
  img_id   INT AUTO_INCREMENT PRIMARY KEY,
  club_id  INT NOT NULL,
  img_path VARCHAR(255) NOT NULL,
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- STEP 8: event_resources table (if not present)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_resources (
  event_id    INT NOT NULL,
  resource_id INT NOT NULL,
  quantity    INT NOT NULL DEFAULT 1,
  PRIMARY KEY (event_id, resource_id),
  FOREIGN KEY (event_id)    REFERENCES events(event_id)       ON DELETE CASCADE,
  FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- STEP 9: resource_requests table (Phase 4 workflow)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resource_requests (
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

-- -------------------------------------------------------------
-- STEP 10: activity_logs table (Phase 8)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
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

-- -------------------------------------------------------------
-- STEP 11: attendance table (ensure correct structure)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
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

-- -------------------------------------------------------------
-- STEP 12: certificates table
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certificates (
  cert_id    INT AUTO_INCREMENT PRIMARY KEY,
  event_id   INT NOT NULL,
  user_id    INT NOT NULL,
  issue_date DATE,
  cert_path  VARCHAR(255),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- STEP 13: user_activity table (for recommendation engine)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_activity (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  user_id          INT NOT NULL,
  event_id         INT NOT NULL,
  interaction_type ENUM('viewed','clicked','attended') NOT NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_view (user_id, event_id),
  FOREIGN KEY (user_id)  REFERENCES users(user_id)   ON DELETE CASCADE,
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------
-- Done (Phase 1)
-- -------------------------------------------------------------

-- =============================================================
-- PHASE 2 MIGRATION — New tables & columns
-- =============================================================

-- STEP P2-1: Add club_email to clubs table
SET @club_email_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clubs' AND COLUMN_NAME = 'club_email'
);
SET @sql_ce = IF(@club_email_exists = 0,
  'ALTER TABLE clubs ADD COLUMN club_email VARCHAR(255)',
  'SELECT 1');
PREPARE _pstmt FROM @sql_ce; EXECUTE _pstmt; DEALLOCATE PREPARE _pstmt;

-- STEP P2-2: club_members table
CREATE TABLE IF NOT EXISTS club_members (
  member_id  INT AUTO_INCREMENT PRIMARY KEY,
  club_id    INT NOT NULL,
  user_id    INT NOT NULL,
  position   ENUM('President','Vice President','Secretary','Treasurer',
                  'Coordinator','Volunteer','Member') NOT NULL DEFAULT 'Member',
  joined_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_member (club_id, user_id),
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- STEP P2-3: membership_requests table
CREATE TABLE IF NOT EXISTS membership_requests (
  request_id INT AUTO_INCREMENT PRIMARY KEY,
  club_id    INT NOT NULL,
  user_id    INT NOT NULL,
  status     ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_request (club_id, user_id),
  FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- STEP P2-4: notifications table
CREATE TABLE IF NOT EXISTS notifications (
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

-- -------------------------------------------------------------
SELECT 'Phase 2 Migration complete.' AS status;
