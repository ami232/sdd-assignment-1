-- Room Allocation schema.
-- Runs on every startup, so every statement must be safe to repeat.
-- trip_id and registration_id are IDs owned by the Trip Management
-- service. They have no foreign keys because those tables live in
-- another service's database.

CREATE TABLE IF NOT EXISTS rooms (
    id       INTEGER PRIMARY KEY,
    trip_id  INTEGER NOT NULL,  -- trip ID from Trip Management, no FK
    name     TEXT    NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity BETWEEN 1 AND 6),
    UNIQUE (trip_id, name)
);

CREATE TABLE IF NOT EXISTS room_assignments (
    id              INTEGER PRIMARY KEY,
    room_id         INTEGER NOT NULL REFERENCES rooms(id),
    registration_id INTEGER NOT NULL UNIQUE  -- one room per person, no FK
);

CREATE TABLE IF NOT EXISTS roommate_preferences (
    id                        INTEGER PRIMARY KEY,
    trip_id                   INTEGER NOT NULL,  -- trip ID, no FK
    registration_id           INTEGER NOT NULL,  -- who is asking, no FK
    preferred_registration_id INTEGER NOT NULL,  -- who they want, no FK
    CHECK (registration_id != preferred_registration_id),
    UNIQUE (registration_id, preferred_registration_id)
);
