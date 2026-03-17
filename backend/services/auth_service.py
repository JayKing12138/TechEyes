"""认证服务：密码哈希与令牌生成"""

import base64
import hashlib
import hmac
import os
import secrets
import time
import logging
from typing import Optional
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from database import get_db
from models.user import User

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """使用 PBKDF2 生成密码哈希（salt$hash）"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码"""
    try:
        salt_b64, digest_b64 = password_hash.split("$", 1)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return hmac.compare_digest(expected, current)
    except Exception:
        return False


def issue_access_token(user_id: int, username: str) -> str:
    """生成简易签名 token（MVP）"""
    secret = os.getenv("AUTH_SECRET", "techeyes-dev-secret")
    payload = f"{user_id}:{username}:{int(time.time())}:{secrets.token_hex(8)}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def verify_access_token(token: str) -> Optional[dict]:
    """校验并解析访问令牌，成功返回用户信息。"""
    if not token:
        return None

    secret = os.getenv("AUTH_SECRET", "techeyes-dev-secret")

    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        payload, signature = raw.rsplit(":", 1)
        expected = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None

        user_id_str, username, issued_at_str, _nonce = payload.split(":", 3)
        user_id = int(user_id_str)
        issued_at = int(issued_at_str)
        now = int(time.time())

        # MVP: 30 天有效期
        if now - issued_at > 30 * 24 * 3600:
            return None

        return {
            "id": user_id,
            "username": username,
            "issued_at": issued_at,
        }
    except Exception:
        return None


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """获取当前用户（从Authorization header）"""
    logger.debug(f"[Auth] Authorization header: {authorization}")
    
    if not authorization:
        logger.debug("[Auth] 无Authorization header")
        return None
    
    # 支持 "Bearer <token>" 格式
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    logger.debug(f"[Auth] Token: {token[:20]}...")
    
    user_info = verify_access_token(token)
    if not user_info:
        logger.debug("[Auth] Token验证失败")
        return None
    
    logger.debug(f"[Auth] Token验证成功，用户ID: {user_info['id']}")
    
    # 验证用户是否存在
    user = db.query(User).filter(User.id == user_info["id"]).first()
    if not user:
        logger.debug(f"[Auth] 用户ID {user_info['id']} 不存在")
        return None
    
    logger.debug(f"[Auth] 用户认证成功: {user.username}")
    
    return {
        "id": user.id,
        "username": user.username,
    }
