"""Trip Management settings, read from environment variables with defaults."""

import os

# Port the web server listens on.
PORT = int(os.environ.get("PORT", "8000"))

# Folder that holds this service's SQLite database file.
DATA_DIR = os.environ.get("DATA_DIR", "./data")

# Full path to the database file inside DATA_DIR.
DB_PATH = os.path.join(DATA_DIR, "trips.db")
