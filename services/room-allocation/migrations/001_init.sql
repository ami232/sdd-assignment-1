-- Room Allocation's first migration: its three tables, with the same rules
-- as the SQLite schema of Assignment 1. Like every migration, it runs once
-- and is never edited after it has been applied; changes go in a new file.
--
-- trip_id and registration_id belong to Trip Management, which has its own
-- database, so they have no foreign keys. Room Allocation checks them by
-- asking Trip Management over HTTP.

CREATE TABLE rooms (
    id       INT IDENTITY PRIMARY KEY,
    trip_id  INT           NOT NULL,  -- trip ID from Trip Management, no FK
    name     NVARCHAR(100) NOT NULL,
    capacity INT           NOT NULL CHECK (capacity BETWEEN 1 AND 6),
    UNIQUE (trip_id, name)
);

CREATE TABLE room_assignments (
    id              INT IDENTITY PRIMARY KEY,
    room_id         INT NOT NULL REFERENCES rooms(id),
    registration_id INT NOT NULL UNIQUE  -- one room per person, no FK
);

CREATE TABLE roommate_preferences (
    id                        INT IDENTITY PRIMARY KEY,
    trip_id                   INT NOT NULL,  -- trip ID, no FK
    registration_id           INT NOT NULL,  -- who is asking, no FK
    preferred_registration_id INT NOT NULL,  -- who they want, no FK
    CHECK (registration_id <> preferred_registration_id),
    UNIQUE (registration_id, preferred_registration_id)
);
