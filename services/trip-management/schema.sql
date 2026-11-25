-- Trip Management schema.
-- Runs on every startup, so every statement must be safe to repeat:
-- IF NOT EXISTS only creates what is missing. Nothing is ever dropped
-- (db.init_db upgrades an older registrations table by copying its rows).

CREATE TABLE IF NOT EXISTS trips (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    destination TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,  -- ISO date, e.g. 2027-01-15
    end_date    TEXT    NOT NULL,
    capacity    INTEGER NOT NULL CHECK (capacity > 0)
);

-- status: pending_payment = place reserved until payment_deadline,
--         confirmed = paid, waitlisted = no free place yet,
--         cancelled = cancelled by the student or the deadline passed.
-- Rows are never deleted, so cancelled history is kept.
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY,
    trip_id INTEGER NOT NULL REFERENCES trips(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE,  -- Python also lowercases; NOCASE covers direct inserts
    status TEXT NOT NULL
        CHECK (status IN (
            'pending_payment',
            'confirmed',
            'waitlisted',
            'cancelled'
        )),
    registered_at TEXT NOT NULL,
    payment_deadline TEXT
);


-- One active registration per email per trip.
-- Cancelled rows are left out, so a cancelled person can register again.
CREATE UNIQUE INDEX IF NOT EXISTS idx_registrations_active_email
    ON registrations (trip_id, email)
    WHERE status IN ('pending_payment', 'confirmed', 'waitlisted');
