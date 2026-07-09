-- =============================================================
-- CECRMS: Club Coordinator Schema Migration v2
-- Adds assigned_at and assigned_by columns to clubs table.
-- Safe to run multiple times (fully idempotent).
-- Compatible with MySQL 8.0+
-- =============================================================

USE cecrms;

-- -------------------------------------------------------------
-- Add assigned_at (timestamp when coordinator was assigned)
-- -------------------------------------------------------------
SET @has_assigned_at = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'clubs'
    AND COLUMN_NAME  = 'assigned_at'
);
SET @sql_aa = IF(@has_assigned_at = 0,
  'ALTER TABLE clubs ADD COLUMN assigned_at TIMESTAMP NULL DEFAULT NULL AFTER coordinator_id',
  'SELECT ''assigned_at already exists'' AS info'
);
PREPARE _s1 FROM @sql_aa; EXECUTE _s1; DEALLOCATE PREPARE _s1;

-- -------------------------------------------------------------
-- Add assigned_by (FK to users: which admin made the assignment)
-- -------------------------------------------------------------
SET @has_assigned_by = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'clubs'
    AND COLUMN_NAME  = 'assigned_by'
);
SET @sql_ab = IF(@has_assigned_by = 0,
  'ALTER TABLE clubs ADD COLUMN assigned_by INT NULL DEFAULT NULL AFTER assigned_at',
  'SELECT ''assigned_by already exists'' AS info'
);
PREPARE _s2 FROM @sql_ab; EXECUTE _s2; DEALLOCATE PREPARE _s2;

-- -------------------------------------------------------------
-- Add FK constraint on assigned_by (only if column was just added)
-- -------------------------------------------------------------
SET @fk_exists = (
  SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
  WHERE TABLE_SCHEMA   = DATABASE()
    AND TABLE_NAME     = 'clubs'
    AND CONSTRAINT_NAME = 'fk_clubs_assigned_by'
);
SET @sql_fk = IF(@fk_exists = 0,
  'ALTER TABLE clubs ADD CONSTRAINT fk_clubs_assigned_by FOREIGN KEY (assigned_by) REFERENCES users(user_id) ON DELETE SET NULL',
  'SELECT ''FK fk_clubs_assigned_by already exists'' AS info'
);
PREPARE _s3 FROM @sql_fk; EXECUTE _s3; DEALLOCATE PREPARE _s3;

-- -------------------------------------------------------------
-- Verify final clubs columns
-- -------------------------------------------------------------
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'clubs'
ORDER BY ORDINAL_POSITION;

SELECT 'Migration v2 complete: assigned_at and assigned_by ensured on clubs.' AS status;
