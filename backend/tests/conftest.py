import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET'] = 'test-only-secret-that-is-at-least-32-characters'
os.environ['DEMO_PASSWORD'] = 'Test-only-password-123!'

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.core.db import Base, SCHEMAS, get_db
from app.main import app
from app.seed import seed


@pytest.fixture
def client():
    postgres_url = os.environ.get('TEST_DATABASE_URL')
    if postgres_url:
        assert make_url(postgres_url).database.endswith('_test'), 'Use uma base exclusiva terminada em _test'
        engine = create_engine(postgres_url)
        with engine.begin() as connection:
            for schema in SCHEMAS:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool,
                               execution_options={'schema_translate_map': {s:None for s in SCHEMAS}})
        @event.listens_for(engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as result:
        yield result
    app.dependency_overrides.clear()
    if postgres_url:
        Base.metadata.drop_all(engine)
    engine.dispose()


def headers(client, username='admin'):
    response = client.post('/api/auth/token', data={'username':username,'password':os.environ['DEMO_PASSWORD']})
    assert response.status_code == 200, response.text
    return {'Authorization':f'Bearer {response.json()["access_token"]}'}
