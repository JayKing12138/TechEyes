"""用户模型"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class User(Base):
    """用户表（PostgreSQL）"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
