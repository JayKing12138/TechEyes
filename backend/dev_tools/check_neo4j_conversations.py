"""检查Neo4j中的对话数据"""
import sys
sys.path.insert(0, '/Users/cairongqing/Documents/techeyes/backend')

from config import Config

def check_neo4j_conversations():
    from neo4j import GraphDatabase
    
    config = Config()
    driver = GraphDatabase.driver(
        config.graph.uri,
        auth=(config.graph.username, config.graph.password)
    )
    
    with driver.session() as session:
        print("\n" + "=" * 80)
        print("💬 Neo4j对话数据检查")
        print("=" * 80)
        
        # 查询所有对话
        result = session.run("""
            MATCH (c:Conversation)
            RETURN c.conversation_id as id, 
                   c.title as title, 
                   c.project_id as project_id,
                   c.user_id as user_id,
                   c.created_at as created_at
            ORDER BY c.created_at DESC
        """)
        
        conversations = list(result)
        
        if not conversations:
            print("\n❌ Neo4j中没有对话记录")
        else:
            print(f"\n找到 {len(conversations)} 条对话记录:\n")
            for conv in conversations:
                print(f"  • 对话ID: {conv['id']}")
                print(f"    标题: {conv['title']}")
                print(f"    项目ID: {conv['project_id']}")
                print(f"    用户ID: {conv['user_id']}")
                print(f"    创建时间: {conv['created_at']}")
                print()
        
        # 按用户统计
        print("\n" + "=" * 80)
        print("📊 按用户统计对话数量:")
        print("=" * 80 + "\n")
        
        result = session.run("""
            MATCH (c:Conversation)
            RETURN c.user_id as user_id, count(c) as count
            ORDER BY user_id
        """)
        
        user_stats = list(result)
        if not user_stats:
            print("  ❌ 无统计数据")
        else:
            for stat in user_stats:
                print(f"   用户ID={stat['user_id']}: {stat['count']} 条对话")
        
        print("\n" + "=" * 80)
    
    driver.close()

if __name__ == "__main__":
    check_neo4j_conversations()
