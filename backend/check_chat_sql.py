"""检查聊天记录 - 使用原生SQL"""

from sqlalchemy import text
from database import engine

try:
    with engine.begin() as conn:
        # 检查会话数量
        result = conn.execute(text("SELECT COUNT(*) FROM conversations"))
        conv_count = result.scalar()
        print(f"📊 数据库中共有 {conv_count} 个会话")
        
        if conv_count > 0:
            print("\n会话列表:")
            result = conn.execute(text("""
                SELECT conversation_id, owner_key, title, created_at 
                FROM conversations 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            for row in result:
                print(f"  - ID: {row[0]}")
                print(f"    所有者: {row[1]}")
                print(f"    标题: {row[2]}")
                print(f"    创建时间: {row[3]}")
                print()
        
        # 检查消息数量
        result = conn.execute(text("SELECT COUNT(*) FROM messages"))
        msg_count = result.scalar()
        print(f"📊 数据库中共有 {msg_count} 条消息")
        
        if msg_count > 0:
            print("\n消息列表（前5条）:")
            result = conn.execute(text("""
                SELECT conversation_id, role, content, created_at 
                FROM messages 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            for row in result:
                print(f"  - 会话ID: {row[0]}")
                print(f"    角色: {row[1]}")
                print(f"    内容: {row[2][:50]}...")
                print(f"    创建时间: {row[3]}")
                print()
        
        if conv_count == 0 and msg_count == 0:
            print("❌ 数据库中没有聊天记录")
            print("\n可能的原因：")
            print("1. 从未创建过会话")
            print("2. 数据库被清空了")
            print("3. 使用了不同的客户端ID")

except Exception as e:
    print(f"❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()
