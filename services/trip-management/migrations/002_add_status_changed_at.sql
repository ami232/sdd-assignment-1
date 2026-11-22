-- 002: record when each registration last changed status (reserved, paid,
-- waitlisted, promoted, cancelled), so organisers can see when it happened.
--
-- registrations already holds rows, so nothing is dropped or recreated:
-- the column is added as nullable, every existing row is filled from
-- registered_at (the last change we know of), and only then is it made
-- NOT NULL, with a default for rows inserted without it.
--
-- The runner sends this file as one batch, and SQL Server checks column
-- names before running a batch, so the statements that use the new column
-- go through EXEC, which is checked only when it runs.

ALTER TABLE registrations ADD status_changed_at DATETIME2 NULL;

EXEC('UPDATE registrations SET status_changed_at = registered_at WHERE status_changed_at IS NULL');

EXEC('ALTER TABLE registrations ALTER COLUMN status_changed_at DATETIME2 NOT NULL');

EXEC('ALTER TABLE registrations ADD CONSTRAINT df_registrations_status_changed_at
      DEFAULT SYSUTCDATETIME() FOR status_changed_at');
