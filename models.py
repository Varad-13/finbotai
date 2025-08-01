from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# DB setup
DATABASE_URL = 'sqlite:///message_history.db'
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# DB operations

def save_message_orm(conversation_id, role, content):
    db = SessionLocal()
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.close()

def get_conversation_messages_orm(conversation_id):
    db = SessionLocal()
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id).all()
    db.close()
    return messages
