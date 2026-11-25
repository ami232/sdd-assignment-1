-- Trip Management's first migration: its two tables, with the same rules
-- as the SQLite schema of Assignment 1. Like every migration, it runs once
-- and is never edited after it has been applied; changes go in a new file.

-- Needed to create the filtered index at the end of this file.
SET QUOTED_IDENTIFIER ON;

CREATE TABLE trips (
    id          INT IDENTITY PRIMARY KEY,
    name        NVARCHAR(200) NOT NULL,
    destination NVARCHAR(200) NOT NULL,
    start_date  DATE          NOT NULL,
    end_date    DATE          NOT NULL,
    capacity    INT           NOT NULL CHECK (capacity > 0)
);

-- status: pending_payment = place reserved until payment_deadline,
--         confirmed = paid, waitlisted = no free place yet,
--         cancelled = cancelled by the student or the deadline passed.
-- Rows are never deleted, so cancelled history is kept.
-- The default collation is case-insensitive, so email comparisons
-- ignore case like COLLATE NOCASE did in SQLite.
CREATE TABLE registrations (
    id               INT IDENTITY PRIMARY KEY,
    trip_id          INT           NOT NULL REFERENCES trips(id),
    name             NVARCHAR(200) NOT NULL,
    email            NVARCHAR(320) NOT NULL,
    status           VARCHAR(20)   NOT NULL
        CHECK (status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled')),
    registered_at    DATETIME2     NOT NULL,
    payment_deadline DATETIME2     NULL
);

-- One active registration per email per trip.
-- Cancelled rows are left out, so a cancelled person can register again.
CREATE UNIQUE INDEX idx_registrations_active_email
    ON registrations (trip_id, email)
    WHERE status IN ('pending_payment', 'confirmed', 'waitlisted');
