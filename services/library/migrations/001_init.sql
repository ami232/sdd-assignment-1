-- owner is plain text because members belong to the group domain (ADR-2)
CREATE TABLE games (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    -- text columns hold 100 characters, the same limit library/service.py checks before saving
    title NVARCHAR(100) NOT NULL,
    owner NVARCHAR(100) NOT NULL,
    min_players INT NOT NULL CHECK (min_players >= 1),
    max_players INT NOT NULL,
    playtime_minutes INT NOT NULL CHECK (playtime_minutes > 0),
    -- SQL Server only allows a check that compares two columns at table level, not on a single column
    CHECK (max_players >= min_players)
);