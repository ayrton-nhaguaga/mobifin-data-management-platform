from alembic import context
from app.core.db import engine, Base, SCHEMAS
import app.models
from sqlalchemy import text

with engine.connect() as connection:
    if engine.dialect.name == 'postgresql':
        for schema in SCHEMAS:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema}'))
        connection.commit()
    context.configure(connection=connection, target_metadata=Base.metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()
