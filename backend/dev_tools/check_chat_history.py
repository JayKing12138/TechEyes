"""检查聊天记录"""

from database import get_db_context
from models import Conversation, ChatMessage

try:
    with get_db_context() as db:
        # 检查会话数量
        conversations = db.query(Conversation).all()
        print(f"📊 数据库中共有 {len(conversations)} 个会话")
        
        if conversations:
            print("\n会话列表:")
            for conv in conversations[:5]:
                print(f"  - ID: {conv.conversation_id}")
                print(f"    标题: {conv.title}")
                print(f"    所有者: {conv.owner_key}")
                print(f"    创建时间: {conv.created_at}")
                print()
        
        # 检查消息数量
        messages = db.query(ChatMessage).all()
        print(f"📊 数据库中共有 {len(messages)} 条消息")
        
        if messages:
            print("\n消息列表（前5条）:")
            for msg in messages[:5]:
                print(f"  - 会话ID: {msg.conversation_id}")
                print(f"    角色: {msg.role}")
                print(f"    内容: {msg.content[:50]}...")
                print()
        
        if not conversations and not messages:
            print("❌ 数据库中没有聊天记录")
            print("\n可能的原因：")
            print("1. 从未创建过会话")
            print("2. 数据库被清空了")
            print("3. 使用了不同的客户端ID")

except Exception as e:
    print(f"❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()
