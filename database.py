import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define models
class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    notes = Column(Text)
    questions = Column(Text)  # Stored as JSON
    flashcards = Column(Text)  # Stored as JSON
    mind_map = Column(Text)  # Stored as JSON
    
# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)

# Database operations
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def save_session(session_data):
    db = get_db()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"session_{timestamp}"
        
        new_session = Session(
            name=session_name,
            summary=session_data.get("summary", ""),
            notes=session_data.get("notes", ""),
            questions=json.dumps(session_data.get("questions", [])),
            flashcards=json.dumps(session_data.get("flashcards", [])),
            mind_map=json.dumps(session_data.get("mind_map", {}))
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return session_name
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def load_session(session_name):
    db = get_db()
    try:
        session = db.query(Session).filter(Session.name == session_name).first()
        if not session:
            return None
            
        return {
            "summary": session.summary,
            "notes": session.notes,
            "questions": json.loads(session.questions) if session.questions else [],
            "flashcards": json.loads(session.flashcards) if session.flashcards else [],
            "mind_map": json.loads(session.mind_map) if session.mind_map else {}
        }
    finally:
        db.close()

def get_all_sessions():
    db = get_db()
    try:
        sessions = db.query(Session).all()
        return [session.name for session in sessions]
    finally:
        db.close()