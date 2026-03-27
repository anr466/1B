from contextlib import contextmanager

from database.database_manager import DatabaseManager

_db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    return _db_manager


def open_db_connection():
    return _db_manager._build_connection(timeout=60.0)


@contextmanager
def get_db_connection():
    with _db_manager.get_connection() as conn:
        yield conn


@contextmanager
def get_db_write_connection():
    with _db_manager.get_write_connection() as conn:
        yield conn
