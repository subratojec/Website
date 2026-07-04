from sqlalchemy import create_engine, Column, String, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cms.db")

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ContentBlock(Base):
    __tablename__ = "content_blocks"
    id = Column(String, primary_key=True, index=True) # e.g. "about_bio", "home_intro"
    content = Column(Text, nullable=False)

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    date = Column(String)
    content = Column(Text)

class Thought(Base):
    __tablename__ = "thoughts"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)

class Postcard(Base):
    __tablename__ = "postcards"
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, nullable=False)

# Create all tables in the engine
Base.metadata.create_all(bind=engine)
