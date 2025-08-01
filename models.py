from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config
Base = declarative_base()

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    name = Column(String(100), nullable=True, default=None)  # new field for tool name
    tool_call_id = Column(String(100), nullable=True, default=None)  # new field for tool call id
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# DB setup
DATABASE_URL = config.DATABASE_URL
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# DB operations

def save_message_orm(conversation_id, role, content, name=None, tool_call_id=None):
    db = SessionLocal()
    message = Message(conversation_id=conversation_id, role=role, content=content, name=name, tool_call_id=tool_call_id)
    db.add(message)
    db.commit()
    db.close()


def get_conversation_messages_orm(conversation_id):
    db = SessionLocal()
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id).all()
    db.close()
    return messages
