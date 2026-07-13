-- migrate_phase_9.sql
-- Phase 9 migrations: notification types
-- NOTE: attendance_code, code_expires_at, and resource_requests.reason
--       were already added in migrate_phase_3_4.sql

USE cecrms;

-- Add type column to notifications (if not already present)
ALTER TABLE notifications
ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'info';


SET SQL_SAFE_UPDATES = 0;


-- Update existing notifications to have a sensible type based on title keyword matching
UPDATE notifications SET type = 'event_created'
  WHERE LOWER(title) LIKE '%event%' AND type = 'info';

UPDATE notifications SET type = 'certificate_generated'
  WHERE LOWER(title) LIKE '%certificate%' AND type = 'info';

UPDATE notifications SET type = 'resource_approved'
  WHERE LOWER(title) LIKE '%approved%' AND type = 'info';

UPDATE notifications SET type = 'resource_rejected'
  WHERE (LOWER(title) LIKE '%rejected%' OR LOWER(title) LIKE '%not approved%') AND type = 'info';

UPDATE notifications SET type = 'club_created'
  WHERE LOWER(title) LIKE '%club%' AND type = 'info';

UPDATE notifications SET type = 'attendance_marked'
  WHERE LOWER(title) LIKE '%attendance%' AND type = 'info';

UPDATE notifications SET type = 'coordinator_assigned'
  WHERE LOWER(title) LIKE '%coordinator%' AND type = 'info';

SET SQL_SAFE_UPDATES = 1;

SELECT 'Phase 9 migration complete.' AS status;
