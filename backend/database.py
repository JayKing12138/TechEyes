"""数据库模块初始化"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os

from config import get_config

config = get_config()

# 创建数据库引擎
engine = create_engine(
    config.database.url,
    echo=config.database.echo,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    # PostgreSQL 特定配置
    pool_pre_ping=True,  # 检查连接是否还有效
    pool_recycle=3600,   # 每小时回收一次连接
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 声明基类
Base = declarative_base()

def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """获取数据库会话（上下文管理器）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """删除数据库（仅在开发时使用）"""
    Base.metadata.drop_all(bind=engine)

# 测试连接
def test_connection():
    """测试数据库连接"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
