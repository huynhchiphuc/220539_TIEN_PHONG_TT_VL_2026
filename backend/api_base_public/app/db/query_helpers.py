from contextlib import contextmanager
from typing import Any, Iterable, Optional

from app.db.mysql_connection import get_mysql_connection


@contextmanager
def db_cursor(dictionary: bool = False, commit: bool = False):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()


def fetch_all(query: str, params: Optional[Iterable[Any]] = None, dictionary: bool = True):
    with db_cursor(dictionary=dictionary) as cursor:
        cursor.execute(query, tuple(params or ()))
        return cursor.fetchall()


def fetch_one(query: str, params: Optional[Iterable[Any]] = None, dictionary: bool = True):
    with db_cursor(dictionary=dictionary) as cursor:
        cursor.execute(query, tuple(params or ()))
        return cursor.fetchone()


def execute(query: str, params: Optional[Iterable[Any]] = None):
    with db_cursor(dictionary=False, commit=True) as cursor:
        cursor.execute(query, tuple(params or ()))
