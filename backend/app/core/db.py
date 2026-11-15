from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

SCHEMAS = ('operational', 'staging', 'warehouse', 'governance', 'quality', 'audit')


class Base(DeclarativeBase):
    pass


def make_engine(url):
    kwargs = {}
    if url.startswith('sqlite'):
        kwargs = {'connect_args': {'check_same_thread': False},
                  'execution_options': {'schema_translate_map': {s: None for s in SCHEMAS}}}
    result = create_engine(url, **kwargs)
    if url.startswith('sqlite'):
        @event.listens_for(result, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return result


engine = make_engine(settings().database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
