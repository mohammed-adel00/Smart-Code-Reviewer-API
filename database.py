import os

from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///reviews.db")
# SQL logging prints every query (including submitted code), so it is opt-in.
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
