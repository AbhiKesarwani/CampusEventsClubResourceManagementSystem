-- =============================================================================
-- CECRMS — One-command Database Reset
--
-- Drops the existing `cecrms` database and rebuilds it from scratch using
-- schema.sql (which creates the database) and seed.sql (demo data).
--
-- IMPORTANT: This script uses MySQL SOURCE with relative paths.
-- It must be run from inside the database/ directory:
--
--   cd database
--   mysql -u root -p < reset_database.sql
--
-- Running from the project root will fail because SOURCE cannot resolve
-- the relative paths schema.sql and seed.sql.
--
-- WARNING: ALL existing data in the `cecrms` database will be permanently
-- deleted. Do not run this against a database with data you want to keep.
-- =============================================================================

DROP DATABASE IF EXISTS cecrms;

SOURCE schema.sql;
SOURCE seed.sql;

SELECT 'CECRMS database reset complete — ready to run the app.' AS status;
