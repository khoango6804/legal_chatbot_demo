from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL - hỗ trợ cả SQLite và PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feedback.db")

# Tạo engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Feedback(Base):
    """Model cho feedback từ người dùng"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)  # Câu hỏi của user
    answer = Column(Text, nullable=False)  # Câu trả lời từ AI
    feedback_type = Column(String(50), nullable=False)  # "wrong", "error", "improvement"
    message = Column(Text)  # Thông điệp feedback từ user
    user_agent = Column(String(500))  # Browser info
    ip_address = Column(String(50))  # IP address (optional)
    is_resolved = Column(Boolean, default=False)  # Đã xử lý chưa
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "feedback_type": self.feedback_type,
            "message": self.message,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# Tạo tables
def init_db():
    """Khởi tạo database và tạo tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

