"""测试Neo4j连接"""

from neo4j import GraphDatabase
from config import get_config

config = get_config()

uri = config.graph.uri
username = config.graph.username
password = config.graph.password

print(f"正在连接到 {uri}...")
print(f"用户名: {username}")
print(f"密码: {password}")

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        result = session.run("RETURN 1 as num")
        print(f"✅ 连接成功！返回值: {result.single()['num']}")
    
    driver.close()
    print("✅ Neo4j连接测试通过！")
    
except Exception as e:
    print(f"❌ 连接失败: {e}")
