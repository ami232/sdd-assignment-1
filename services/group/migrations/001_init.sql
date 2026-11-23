CREATE TABLE members (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    is_active INT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE nights (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    night_date NVARCHAR(10) NOT NULL,
    available_minutes INT NOT NULL CHECK (available_minutes > 0)
);

CREATE TABLE night_attendees (
    night_id INT NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    member_id INT NOT NULL REFERENCES members(id),
    PRIMARY KEY (night_id, member_id)
);

CREATE TABLE night_guests (
    night_id INT NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    guest_name NVARCHAR(100) NOT NULL,
    PRIMARY KEY (night_id, guest_name)
);
-- game_id has no foreign key because games live in the library service's own database (ADR-3)
CREATE TABLE ratings (
    member_id INT NOT NULL REFERENCES members(id),
    game_id INT NOT NULL,
    score INT NOT NULL CHECK (score BETWEEN 1 AND 10),
    PRIMARY KEY (member_id, game_id)
);

CREATE TABLE plays (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    night_id INT NOT NULL REFERENCES nights(id) ON DELETE CASCADE,
    game_id INT NOT NULL
);