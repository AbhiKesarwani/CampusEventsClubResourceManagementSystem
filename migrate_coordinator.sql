-- CECRMS: Add assigned_at column to clubs table
-- Safe to run multiple times (idempotent)
USE cecrms;

SET @assigned_at_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clubs' AND COLUMN_NAME = 'assigned_at'
);
SET @sql_aa = IF(@assigned_at_exists = 0,
  'ALTER TABLE clubs ADD COLUMN assigned_at TIMESTAMP NULL DEFAULT NULL',
  'SELECT 1 -- assigned_at already exists');
PREPARE _stmt_aa FROM @sql_aa; EXECUTE _stmt_aa; DEALLOCATE PREPARE _stmt_aa;

SELECT 'Migration complete: assigned_at column ensured.' AS status;
