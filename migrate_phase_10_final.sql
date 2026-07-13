-- =============================================================
-- CECRMS Phase 10 Final Migration
-- Safe / idempotent. Run on existing cecrms database.
-- =============================================================
USE cecrms;
SET SQL_SAFE_UPDATES = 0;

-- ── events: OTP columns ────────────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='events' AND COLUMN_NAME='attendance_otp');
SET @sql = IF(@col=0,
  'ALTER TABLE events ADD COLUMN attendance_otp VARCHAR(6) NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='events' AND COLUMN_NAME='otp_generated_at');
SET @sql = IF(@col=0,
  'ALTER TABLE events ADD COLUMN otp_generated_at DATETIME NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── events: category for recommendations ───────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='events' AND COLUMN_NAME='category');
SET @sql = IF(@col=0,
  'ALTER TABLE events ADD COLUMN category VARCHAR(100) NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── resource_requests: new workflow fields ─────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='required_date');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN required_date DATE NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='req_start_time');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN req_start_time TIME NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='req_end_time');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN req_end_time TIME NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='purpose');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN purpose TEXT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='remarks');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN remarks TEXT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='resource_requests' AND COLUMN_NAME='auto_released');
SET @sql = IF(@col=0,
  'ALTER TABLE resource_requests ADD COLUMN auto_released TINYINT(1) NOT NULL DEFAULT 0',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── notifications: event_key for dedup ────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='notifications' AND COLUMN_NAME='event_key');
SET @sql = IF(@col=0,
  'ALTER TABLE notifications ADD COLUMN event_key VARCHAR(150) NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- Unique index on (user_id, event_key) — skips NULLs automatically
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='notifications' AND INDEX_NAME='ux_notif_dedup');
SET @sql = IF(@idx=0,
  'CREATE UNIQUE INDEX ux_notif_dedup ON notifications (user_id, event_key)',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- ── clubs: image_path for logo ────────────────────────────────
SET @col = (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='clubs' AND COLUMN_NAME='image_path');
SET @sql = IF(@col=0,
  'ALTER TABLE clubs ADD COLUMN image_path VARCHAR(255) NULL DEFAULT NULL',
  'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET SQL_SAFE_UPDATES = 1;
SELECT 'Phase 10 Final migration complete.' AS status;
