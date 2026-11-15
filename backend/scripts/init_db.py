from app.core.db import SessionLocal
from app.seed import seed

with SessionLocal() as db:
    seed(db)
