from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# DB setup
DATABASE_URL = 'sqlite:///message_history.db'
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# DB operations

def save_message_orm(role, content):
    db = SessionLocal()
    message = Message(role=role, content=content)
    db.add(message)
    db.commit()
    db.close()

def get_all_messages_orm():
    db = SessionLocal()
    messages = db.query(Message).order_by(Message.id).all()
    db.close()
    return messages
