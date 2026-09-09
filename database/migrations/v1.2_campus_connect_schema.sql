-- =============================================================
-- CECRMS Phase 13 Migration — Campus Connect Schema Completion
-- Idempotent / safe to re-run on existing cecrms database.
-- =============================================================
USE cecrms;

-- ── cc_conversation_state: per-user archive/delete flags ──────
-- Absent from Phase 12; required by connect_service.py's get_inbox,
-- send_message, delete_conversation, set_conversation_archived.
CREATE TABLE IF NOT EXISTS cc_conversation_state (
  user_id    INT NOT NULL,
  other_id   INT NOT NULL,
  is_archived TINYINT(1) DEFAULT 0,
  is_deleted  TINYINT(1) DEFAULT 0,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, other_id),
  FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (other_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ── read_at: read-receipt timestamp on cc_messages ────────────
-- Referenced by mark_messages_read() but not in Phase 12 schema.
ALTER TABLE cc_messages
  MODIFY COLUMN read_at TIMESTAMP NULL DEFAULT NULL;

-- (No-op if column already exists; ALTER MODIFY is safe to re-run.)
-- If column is missing, run the following instead:
-- ALTER TABLE cc_messages ADD COLUMN read_at TIMESTAMP NULL DEFAULT NULL;

SELECT 'Phase 13 migration complete.' AS status;
