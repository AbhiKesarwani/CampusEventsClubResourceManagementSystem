-- =============================================================================
-- CECRMS v1.3 migration — fix cc_ai_history.source ENUM
-- Idempotent / safe to re-run on an existing cecrms database.
--
-- Root cause: routes/connect.py calls
--     connect_service.save_ai_message(..., source='user')
-- for user questions, but the original ENUM only allowed ('db','ai','escalated').
-- MySQL 8.0 strict mode (the default) rejects the INSERT and the exception is
-- silently swallowed, so AI history is never persisted.
--
-- This migration adds the 'user' value to the ENUM so user questions are
-- correctly stored.  The 'escalated' value is kept as-is for escalated
-- coordinator notifications.
--
-- Usage:
--   mysql -u root -p cecrms < database/migrations/v1.3_ai_history_source_enum.sql
-- =============================================================================
USE cecrms;

ALTER TABLE cc_ai_history
  MODIFY COLUMN source
    ENUM('db','ai','escalated','user') NOT NULL DEFAULT 'ai';

SELECT 'v1.3 migration complete — cc_ai_history.source ENUM now includes user.' AS status;
