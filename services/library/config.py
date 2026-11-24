import os

DEFAULT_PORT = 8000
MIN_PORT = 1
MAX_PORT = 65535

def get_port() -> int:
    """return the port from PORT or the default if it is missing or invalid"""
    port_text = os.environ.get("PORT", str(DEFAULT_PORT))
    try:
        port = int(port_text)
    except ValueError:
        print(f"PORT={port_text} is not a number, using {DEFAULT_PORT}")
        return DEFAULT_PORT

    if port < MIN_PORT or port > MAX_PORT:
        print(f"PORT={port} is out of range, using {DEFAULT_PORT}")
        return DEFAULT_PORT
    return port


DEFAULT_APP_VERSION = "dev"

def get_app_version() -> str:
    """return the git commit the image was built from, which the deploy pipeline sets, or dev when running locally"""
    return os.environ.get("APP_VERSION", DEFAULT_APP_VERSION)

DEFAULT_CORS_ORIGIN = "http://localhost:8080"


def get_cors_origin() -> str:
    """return the one web address allowed to call this service from a browser, which is where the UI is served"""
    return os.environ.get("CORS_ORIGIN", DEFAULT_CORS_ORIGIN)

def get_database_url() -> str:
    """return the connection string from DATABASE_URL, which has no default because it contains a password"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set, for example mssql://library_user:password@localhost:1433/library_db")
    return database_url
