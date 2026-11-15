"""Local development launcher with migrations and seed; never prints secrets."""
import argparse
import os
from pathlib import Path
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', action='store_true', help='Use SQLite instead of local PostgreSQL')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    backend_dir = Path(__file__).resolve().parents[1]
    os.chdir(backend_dir)
    config = dotenv_values(backend_dir.parent / '.env')
    for key in ('JWT_SECRET', 'DEMO_PASSWORD'):
        if not os.environ.get(key) and config.get(key):
            os.environ[key] = config[key]
    if args.sqlite:
        os.environ['DATABASE_URL'] = 'sqlite:///./local.db'
    elif not os.environ.get('DATABASE_URL'):
        password = config.get('POSTGRES_PASSWORD')
        if not password:
            raise SystemExit('Configure .env primeiro')
        os.environ['DATABASE_URL'] = f'postgresql+psycopg://mobifin:{password}@127.0.0.1:55432/mobifin?connect_timeout=5'
    from alembic.config import Config
    from alembic import command
    command.upgrade(Config('alembic.ini'), 'head')
    from app.core.db import SessionLocal
    from app.seed import seed
    with SessionLocal() as db:
        seed(db)
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
