"""用户雷达画像模型"""

from sqlalchemy import Column, BigInteger, Integer, DateTime, Text, Index
from sqlalchemy.sql import func
from database import Base


class UserRadarProfile(Base):
    """用户画像表（跨新闻维度的长期偏好与兴趣）"""

    __tablename__ = "user_radar_profiles"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    profile_json = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_user_radar_profile", "user_id"),
    )
