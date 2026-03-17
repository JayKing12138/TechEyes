#!/usr/bin/env python3
"""
测试脚本：验证空对话是否会在列表中显示
"""
from sqlalchemy import text, create_engine
import os

# 读取数据库URL
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db_url = line.strip().split('=', 1)[1].strip('"\'')
            break

engine = create_engine(db_url)

# 获取某个用户的对话列表
owner_key = "test_user_123"

with engine.begin() as conn:
    # 先看看未过滤的所有对话
    print("=" * 60)
    print("🔍 检查未过滤的所有对话:")
    print("=" * 60)
    rows = conn.execute(
        text("SELECT conversation_id, title, owner_key FROM conversations WHERE owner_key = :owner_key LIMIT 10"),
        {"owner_key": owner_key}
    ).mappings().all()
    
    for row in rows:
        print(f"  - {row['conversation_id']}: {row['title']}")
    
    if not rows:
        print("  (无对话)")
    
    # 再看看有消息的对话（使用新的过滤条件）
    print("\n" + "=" * 60)
    print("✅ 检查有消息的对话（应用新过滤条件）:")
    print("=" * 60)
    rows = conn.execute(
        text("""
            SELECT c.conversation_id, c.title, c.owner_key,
                   (SELECT COUNT(*) FROM messages WHERE conversation_id = c.conversation_id) as msg_count
            FROM conversations c
            WHERE c.owner_key = :owner_key
            AND EXISTS (SELECT 1 FROM messages WHERE conversation_id = c.conversation_id)
            LIMIT 10
        """),
        {"owner_key": owner_key}
    ).mappings().all()
    
    for row in rows:
        print(f"  - {row['conversation_id']}: {row['title']} ({row['msg_count']}条消息)")
    
    if not rows:
        print("  (无有效对话)")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("📊 统计信息:")
    print("=" * 60)
    
    # 总对话数
    total = conn.execute(
        text("SELECT COUNT(*) as cnt FROM conversations WHERE owner_key = :owner_key"),
        {"owner_key": owner_key}
    ).scalar() or 0
    
    # 有消息的对话数
    with_msgs = conn.execute(
        text("""
            SELECT COUNT(*) as cnt FROM conversations c 
            WHERE c.owner_key = :owner_key 
            AND EXISTS (SELECT 1 FROM messages WHERE conversation_id = c.conversation_id)
        """),
        {"owner_key": owner_key}
    ).scalar() or 0
    
    # 空对话数
    empty = total - with_msgs
    
    print(f"  总对话数: {total}")
    print(f"  有消息的对话: {with_msgs}")
    print(f"  空对话（将被过滤）: {empty}")
    
    if empty > 0:
        print(f"\n✅ 过滤生效！{empty}个空对话将不会显示在列表中")
    else:
        print(f"\n✓ 目前没有空对话")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60)
