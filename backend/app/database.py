from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def migrate_schema() -> None:
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(drill_questions)"))}
        if cols and "choices_json" not in cols:
            conn.execute(text("ALTER TABLE drill_questions ADD COLUMN choices_json VARCHAR(200)"))
        if cols and "image_url" not in cols:
            conn.execute(text("ALTER TABLE drill_questions ADD COLUMN image_url VARCHAR(120)"))
        session_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(drill_sessions)"))}
        if session_cols and "passage_title" not in session_cols:
            conn.execute(text("ALTER TABLE drill_sessions ADD COLUMN passage_title VARCHAR(80)"))
        if session_cols and "passage" not in session_cols:
            conn.execute(text("ALTER TABLE drill_sessions ADD COLUMN passage VARCHAR(900)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
