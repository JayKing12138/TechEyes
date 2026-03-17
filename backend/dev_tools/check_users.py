"""检查数据库中的用户"""

from database import get_db_context
from models.user import User

with get_db_context() as db:
    users = db.query(User).all()
    print(f"数据库中共有 {len(users)} 个用户：")
    print()
    for user in users:
        print(f"  ID: {user.id}")
        print(f"  用户名: {user.username}")
        print()
