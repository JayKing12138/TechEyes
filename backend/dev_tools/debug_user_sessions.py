"""检查登录用户的会话数据"""

from sqlalchemy import text
from database import engine

print("请告诉我你登录的用户ID是多少？")
print()
print("数据库中的用户会话：")
print()

with engine.begin() as conn:
    # 检查所有会话及其所有者
    result = conn.execute(text("""
        SELECT c.conversation_id, c.owner_key, c.title, c.created_at 
        FROM conversations c
        ORDER BY c.created_at DESC
    """))
    
    rows = result.fetchall()
    
    for row in rows:
        print(f"  所有者: {row[1]}")
        print(f"  标题: {row[2]}")
        print(f"  创建时间: {row[3]}")
        print()

print("\n如果你登录的用户ID是2或3，应该能看到会话。")
print("如果看不到，可能是前端token设置有问题。")
