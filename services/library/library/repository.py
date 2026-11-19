import json
import os
from contextlib import closing

import pymssql

import database

LIBRARY_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_FILE_PATH = os.path.join(LIBRARY_DIR, "seed.json")

GAME_COLUMNS = "id, title, owner, min_players, max_players, playtime_minutes"


def seed_games() -> int:
    """load the seed games into an empty games table and return how many were added"""
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) AS game_count FROM games")
        game_count = cursor.fetchone()["game_count"]
        # only seed a fresh database so restarts never duplicate or overwrite games
        if game_count > 0:
            return 0

        try:
            with open(SEED_FILE_PATH, encoding="utf-8") as seed_file:
                seed_data = json.load(seed_file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Could not read seed file {SEED_FILE_PATH}: {error}") from error

        for game in seed_data:
            _insert_game(cursor, game)
        # one commit at the end so a broken seed file never leaves half the games behind
        connection.commit()
        return len(seed_data)


def add_game(game: dict) -> int:
    """save a game that has already been validated and return its new id"""
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        game_id = _insert_game(cursor, game)
        connection.commit()
        return game_id


def list_games() -> list[dict]:
    """return every game in the library, sorted by title"""
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute(f"SELECT {GAME_COLUMNS} FROM games ORDER BY title")
        games = cursor.fetchall()
    return games


def find_games_that_fit(players: int, minutes: int) -> list[dict]:
    """return the games that support this many players and fit in this many minutes"""
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT {GAME_COLUMNS} FROM games"
            " WHERE min_players <= %s AND max_players >= %s AND playtime_minutes <= %s"
            " ORDER BY title",
            (players, players, minutes),
        )
        games = cursor.fetchall()
    return games


def get_game_title(game_id: int) -> str | None:
    """return the title of a game, or None if no game has that id"""
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT title FROM games WHERE id = %s", (game_id,))
        row = cursor.fetchone()
    if row is None:
        return None
    return row["title"]


def _insert_game(cursor: pymssql.Cursor, game: dict) -> int:
    """insert one game without committing and return its new id"""
    # OUTPUT INSERTED.id hands back the id SQL Server just generated, in the same statement
    cursor.execute(
        "INSERT INTO games (title, owner, min_players, max_players, playtime_minutes)"
        " OUTPUT INSERTED.id"
        " VALUES (%s, %s, %s, %s, %s)",
        (
            game["title"],
            game["owner"],
            game["min_players"],
            game["max_players"],
            game["playtime_minutes"],
        ),
    )
    return cursor.fetchone()["id"]