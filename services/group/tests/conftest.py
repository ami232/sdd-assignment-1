from contextlib import closing

import pytest

import database

# children first, because members and nights can't be deleted while other rows still point at them
GROUP_TABLES = ["plays", "ratings", "night_guests", "night_attendees", "nights", "members"]


@pytest.fixture(autouse=True)
def empty_group_database():
    """bring the test database up to date and empty every group table, so every test starts from nothing"""
    database.run_migrations()
    with closing(database.get_connection()) as connection:
        cursor = connection.cursor()
        for table_name in GROUP_TABLES:
            cursor.execute(f"DELETE FROM {table_name}")
        connection.commit()