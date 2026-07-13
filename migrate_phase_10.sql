-- =============================================================
-- CECRMS Phase 10 Migration
-- Ensures attendance_code columns and student self-submit support
-- Safe to run multiple times (uses IF NOT EXISTS patterns)
-- =============================================================

USE cecrms;

-- Add attendance_code to events if not present
SET @ac_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
    AND COLUMN_NAME = 'attendance_code'
);
SET @sql_ac = IF(@ac_exists = 0,
  'ALTER TABLE events ADD COLUMN attendance_code VARCHAR(20) NULL DEFAULT NULL',
  'SELECT 1');
PREPARE _stmt_ac FROM @sql_ac;
EXECUTE _stmt_ac;
DEALLOCATE PREPARE _stmt_ac;

-- Add code_expires_at to events if not present
SET @ce_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
    AND COLUMN_NAME = 'code_expires_at'
);
SET @sql_ce = IF(@ce_exists = 0,
  'ALTER TABLE events ADD COLUMN code_expires_at DATETIME NULL DEFAULT NULL',
  'SELECT 1');
PREPARE _stmt_ce FROM @sql_ce;
EXECUTE _stmt_ce;
DEALLOCATE PREPARE _stmt_ce;

-- Add unique index on attendance_code (if not present)
SET @idx_exists = (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'events'
    AND INDEX_NAME = 'ux_events_attendance_code'
);
SET @sql_idx = IF(@idx_exists = 0,
  'CREATE UNIQUE INDEX ux_events_attendance_code ON events (attendance_code)',
  'SELECT 1');
PREPARE _stmt_idx FROM @sql_idx;
EXECUTE _stmt_idx;
DEALLOCATE PREPARE _stmt_idx;

-- Add scan_by to attendance if not present (who marked it)
SET @sb_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'attendance'
    AND COLUMN_NAME = 'scan_by'
);
SET @sql_sb = IF(@sb_exists = 0,
  'ALTER TABLE attendance ADD COLUMN scan_by INT NULL DEFAULT NULL',
  'SELECT 1');
PREPARE _stmt_sb FROM @sql_sb;
EXECUTE _stmt_sb;
DEALLOCATE PREPARE _stmt_sb;

-- Add scan_time to attendance if not present
SET @st_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'attendance'
    AND COLUMN_NAME = 'scan_time'
);
SET @sql_st = IF(@st_exists = 0,
  'ALTER TABLE attendance ADD COLUMN scan_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
  'SELECT 1');
PREPARE _stmt_st FROM @sql_st;
EXECUTE _stmt_st;
DEALLOCATE PREPARE _stmt_st;

-- Ensure reason column exists in resource_requests
SET @rr_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource_requests'
    AND COLUMN_NAME = 'reason'
);
SET @sql_rr = IF(@rr_exists = 0,
  'ALTER TABLE resource_requests ADD COLUMN reason TEXT NULL',
  'SELECT 1');
PREPARE _stmt_rr FROM @sql_rr;
EXECUTE _stmt_rr;
DEALLOCATE PREPARE _stmt_rr;

SELECT 'Phase 10 migration complete.' AS status;
