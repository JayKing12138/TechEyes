"""检查token验证失败的原因"""

import base64
import hmac
import hashlib
import time
from config import get_config

config = get_config()
secret = config.auth.secret_key

# 模拟前端可能发送的token
test_tokens = [
    "test_token",
    "invalid_token",
    "expired_token",
]

print("Token验证失败的可能原因：")
print()
print("1. Token过期（30天有效期）")
print("2. Token签名不匹配")
print("3. Token格式错误")
print("4. 用户不存在")
print()
print("当前配置：")
print(f"  - Secret Key: {secret[:10]}...")
print(f"  - Token有效期: 30天")
print()
print("解决方案：")
print("  在浏览器控制台运行：")
print("  localStorage.removeItem('techeyes_auth_token')")
print("  location.reload()")
