"""检查Neo4j中的关系数据"""

from neo4j import GraphDatabase
from config import get_config

config = get_config()

uri = config.graph.uri
username = config.graph.username
password = config.graph.password

print(f"正在连接到 {uri}...")

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        # 检查新闻数量
        result = session.run("MATCH (n:News) RETURN count(n) as count")
        news_count = result.single()['count']
        print(f"✅ 新闻数量: {news_count}")
        
        # 检查实体数量
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        entity_count = result.single()['count']
        print(f"✅ 实体数量: {entity_count}")
        
        # 检查关系数量
        result = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) as count")
        relation_count = result.single()['count']
        print(f"✅ 关系数量: {relation_count}")
        
        # 检查一条新闻的关系
        result = session.run("""
            MATCH (n:News)-[r:MENTIONS]->(e:Entity)
            RETURN n.title as title, e.name as entity_name, e.type as entity_type, r.salience as salience
            LIMIT 5
        """)
        
        print("\n示例关系数据:")
        for record in result:
            print(f"  - 新闻: {record['title'][:30]}...")
            print(f"    实体: {record['entity_name']} ({record['entity_type']})")
            print(f"    重要性: {record['salience']}")
            print()
    
    driver.close()
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
