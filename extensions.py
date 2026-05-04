# Source Generated with Decompyle++
# File: extensions.cpython-310.pyc (Python 3.10)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
db = SQLAlchemy()
migrate = Migrate()

def set_sqlite_pragma(dbapi_connection, connection_record):
    '''Active les clés étrangères SQLite à chaque connexion.'''
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
        return None

set_sqlite_pragma = event.listens_for(Engine, 'connect')(set_sqlite_pragma)
