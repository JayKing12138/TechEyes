#!/bin/bash
# 快速验证 TechEyes 系统修复

echo "=================================="
echo "🔍 TechEyes 系统验证脚本"
echo "=================================="
echo ""

cd /Users/cairongqing/Documents/techeyes/backend

echo "1️⃣ 检查PostgreSQL数据..."
conda run -n techeyes python -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from models.user import User
from models.project import Project

db = SessionLocal()
users = db.query(User).all()
print(f'\n✅ 用户总数: {len(users)}')

for user in users:
    project_count = db.query(Project).filter(Project.user_id == user.id).count()
    status = '✅' if project_count > 0 else '❌'
    print(f'{status} {user.username} (ID={user.id}): {project_count}个项目')

db.close()
"

echo ""
echo "2️⃣ 检查Neo4j对话数据..."
conda run -n techeyes python -c "
import sys
sys.path.insert(0, '.')
from config import Config
from neo4j import GraphDatabase

config = Config()
driver = GraphDatabase.driver(
    config.graph.uri,
    auth=(config.graph.username, config.graph.password)
)

with driver.session() as session:
    result = session.run('MATCH (c:Conversation) RETURN count(c) as count').single()
    conv_count = result['count']
    print(f'✅ 对话总数: {conv_count}')
    
    result = session.run('''
        MATCH (c:Conversation)
        RETURN c.user_id as user_id, count(c) as count
        ORDER BY user_id
    ''')
    
    for record in result:
        print(f'   用户ID={record[\"user_id\"]}: {record[\"count\"]}条对话')

driver.close()
"

echo ""
echo "3️⃣ 测试认证服务..."
conda run -n techeyes python -c "
import sys
sys.path.insert(0, '.')
from services.auth_service import get_current_user
print('✅ auth_service.py 导入成功，无logger错误')
"

echo ""
echo "=================================="
echo "✅ 验证完成！"
echo "=================================="
echo ""
echo "现在可以："
echo "1. 重启后端: cd backend && conda run -n techeyes python main.py"
echo "2. 使用 zzm 或 crq 账号登录测试"
echo "3. 检查项目知识工作台和智能决策问答"
echo ""
