-- =============================================================================
-- CECRMS — v1.1 incremental migration (Profile & Settings)
-- Idempotent: safe to run multiple times against an existing `cecrms`
-- database that was built from an earlier v1.0.0 schema.sql. Fresh installs
-- don't need this — database/schema.sql already includes these columns.
--
-- Usage:  mysql -u root -p cecrms < database/migrations/v1.1_profile_settings.sql
-- =============================================================================
USE cecrms;

SET @col := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'avatar_path');
SET @sql := IF(@col = 0,
  'ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255) DEFAULT NULL',
  'SELECT ''users.avatar_path already exists'' AS note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col := (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'preferences');
SET @sql := IF(@col = 0,
  'ALTER TABLE users ADD COLUMN preferences JSON DEFAULT NULL',
  'SELECT ''users.preferences already exists'' AS note');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT 'v1.1 migration complete — users.avatar_path / users.preferences ensured.' AS status;
