from contextlib import closing

import pytest

import database


@pytest.fixture(autouse=True)
def empty_library():
    """bring the test database up to date and empty the games table, so every test starts from nothing"""
    database.run_migrations()
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        # TRUNCATE also restarts the id counter, so the first game of every test gets id 1 again
        cursor.execute("TRUNCATE TABLE games")
        connection.commit()