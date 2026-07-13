-- CECRMS — Phase 3 & 4 Migration
-- Safe version without IF NOT EXISTS (not supported on older MySQL for ADD COLUMN)

USE cecrms;

-- Phase 3: Attendance Code on Events
-- Ignore error if columns already exist
ALTER TABLE events ADD COLUMN attendance_code VARCHAR(20) DEFAULT NULL;
ALTER TABLE events ADD COLUMN code_expires_at DATETIME DEFAULT NULL;
ALTER TABLE events ADD INDEX idx_attendance_code (attendance_code);

-- Phase 4: Reason on Resource Requests
ALTER TABLE resource_requests ADD COLUMN reason TEXT DEFAULT NULL;

SELECT 'Migration complete.' AS status;
