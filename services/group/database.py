import os
import time
from contextlib import closing
from urllib.parse import unquote, urlparse

import pymssql

import config

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
DEFAULT_SQL_SERVER_PORT = 1433
LOGIN_TIMEOUT_SECONDS = 10
CONNECT_ATTEMPTS = 8
FIRST_RETRY_DELAY_SECONDS = 2
MAX_RETRY_DELAY_SECONDS = 30


def get_connection() -> pymssql.Connection:
    """open a connection to this service's own database, with every row returned as a dict"""
    url = urlparse(config.get_database_url())
    port = url.port or DEFAULT_SQL_SERVER_PORT
    return pymssql.connect(
        server=url.hostname,
        port=str(port),
        user=unquote(url.username),
        password=unquote(url.password),
        database=url.path.lstrip("/"),
        login_timeout=LOGIN_TIMEOUT_SECONDS,
        as_dict=True,
    )


def wait_for_database() -> None:
    """keep trying to connect with growing pauses, because a paused Azure database needs about a minute to wake up"""
    delay_seconds = FIRST_RETRY_DELAY_SECONDS
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            connection = get_connection()
            connection.close()
            return
        except pymssql.OperationalError as error:
            if attempt == CONNECT_ATTEMPTS:
                raise RuntimeError(f"database still unreachable after {CONNECT_ATTEMPTS} attempts") from error
            print(f"Database not ready (attempt {attempt} of {CONNECT_ATTEMPTS}), retrying in {delay_seconds}s: {error}")
            time.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2, MAX_RETRY_DELAY_SECONDS)


def run_migrations() -> None:
    """apply every migration file this database has not recorded yet, in the order of their numbers"""
    with closing(get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "IF OBJECT_ID('schema_migrations') IS NULL"
            " CREATE TABLE schema_migrations ("
            " version NVARCHAR(255) PRIMARY KEY,"
            " applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME())"
        )
        connection.commit()

        cursor.execute("SELECT version FROM schema_migrations")
        applied_versions = []
        for row in cursor.fetchall():
            applied_versions.append(row["version"])

        applied_count = 0
        # the zero-padded numbers in the file names make alphabetical order the same as number order
        for file_name in sorted(os.listdir(MIGRATIONS_DIR)):
            if file_name.endswith(".sql") and file_name not in applied_versions:
                _apply_migration(connection, file_name)
                applied_count = applied_count + 1

    if applied_count == 0:
        print("Database is up to date, no migrations to apply")


def _apply_migration(connection: pymssql.Connection, file_name: str) -> None:
    """run one migration and record it in the same transaction, so it is either fully applied or not at all"""
    with open(os.path.join(MIGRATIONS_DIR, file_name), encoding="utf-8") as migration_file:
        migration_sql = migration_file.read()

    cursor = connection.cursor()
    try:
        cursor.execute(migration_sql)
        cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (file_name,))
        connection.commit()
    except pymssql.Error:
        connection.rollback()
        raise
    print(f"Applied migration {file_name}")