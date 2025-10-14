import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URL = "mysql+pymysql://{u}:{p}@{h}:{port}/{n}?charset=utf8mb4".format(
    u=os.getenv("DB_USER", "dbuser211702"),
    p=os.getenv("DB_PASS", "ce1234"),
    h=os.getenv("DB_HOST", "earth.gwangju.ac.kr"),
    port=os.getenv("DB_PORT", "3306"),
    n=os.getenv("DB_NAME", "db211702"),
)

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=3600, isolation_level="READ COMMITTED")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
