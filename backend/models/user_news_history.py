"""用户新闻历史模型"""

from sqlalchemy import Column, BigInteger, String, DateTime, Text, Integer, Float, Index
from sqlalchemy.sql import func
from database import Base


class UserNewsHistory(Base):
    """用户新闻查看历史表（雷达档案）"""
    __tablename__ = "user_news_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    news_id = Column(String(64), nullable=False, index=True)
    
    news_title = Column(String(512))
    news_url = Column(String(1024))
    news_snippet = Column(Text)
    
    view_count = Column(Integer, default=1)
    last_viewed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    first_viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    analysis_count = Column(Integer, default=0)
    report_generated = Column(Integer, default=0)
    
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_user_news', 'user_id', 'news_id'),
        Index('idx_last_viewed', 'user_id', 'last_viewed_at'),
    )
