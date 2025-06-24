import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use SQLite in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"  # 创建本地文件数据库

# Create the SQLAlchemy engine for in-memory SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Add this function to create all tables
def init_db():
    Base.metadata.create_all(bind=engine)