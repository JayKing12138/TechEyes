"""为用户创建测试数据（项目和对话）"""
import sys
sys.path.insert(0, '/Users/cairongqing/Documents/techeyes/backend')

from database import SessionLocal
from models.user import User
from models.project import Project
from config import Config
from neo4j import GraphDatabase
from datetime import datetime
import uuid

def create_test_data_for_user(username: str):
    """为指定用户创建测试数据"""
    db = SessionLocal()
    config = Config()
    neo4j_driver = GraphDatabase.driver(
        config.graph.uri,
        auth=(config.graph.username, config.graph.password)
    )
    
    try:
        # 1. 查找用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return
        
        print(f"\n找到用户: {user.username} (ID={user.id})")
        
        # 2. 检查是否已有项目
        existing_projects = db.query(Project).filter(Project.user_id == user.id).all()
        if existing_projects:
            print(f"\n⚠️  用户已有 {len(existing_projects)} 个项目:")
            for proj in existing_projects:
                print(f"   • {proj.name} (ID={proj.id})")
            
            choice = input("\n是否要创建新项目? (y/n): ").strip().lower()
            if choice != 'y':
                print("取消创建")
                return
        
        # 3. 创建项目
        print("\n" + "=" * 80)
        print("创建测试项目...")
        print("=" * 80)
        
        project = Project(
            name="智能决策问答",
            description="基于AI的智能决策问答系统项目",
            user_id=user.id,
            created_at=datetime.utcnow()
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        print(f"✅ 创建项目: {project.name} (ID={project.id})")
        
        # 4. 在Neo4j中创建对话
        print("\n创建测试对话...")
        
        conv_id = str(uuid.uuid4())
        
        with neo4j_driver.session() as session:
            # 创建对话节点
            session.run("""
                CREATE (c:Conversation {
                    conversation_id: $conv_id,
                    title: $title,
                    project_id: $project_id,
                    user_id: $user_id,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                """, 
                conv_id=conv_id,
                title="如何制定AI芯片发展战略?",
                project_id=project.id,
                user_id=user.id
            )
            
            # 创建一些测试消息
            messages = [
                {
                    "msg_id": str(uuid.uuid4()),
                    "role": "user",
                    "content": "请帮我分析当前AI芯片市场的主要竞争格局",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "msg_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": "当前AI芯片市场呈现以下竞争格局:\n\n1. **英伟达(NVIDIA)**: 市场领导者，占据约80%的AI训练芯片市场份额\n2. **AMD**: 主要竞争对手，MI系列GPU逐渐获得市场认可\n3. **中国厂商**: 包括华为、寒武纪、海光等，在国内市场份额提升\n\n建议重点关注:\n- 技术创新趋势\n- 供应链安全\n- 应用场景拓展",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            for i, msg in enumerate(messages):
                session.run("""
                    MATCH (c:Conversation {conversation_id: $conv_id})
                    CREATE (m:Message {
                        message_id: $msg_id,
                        role: $role,
                        content: $content,
                        timestamp: datetime($timestamp),
                        sequence: $sequence
                    })
                    CREATE (c)-[:HAS_MESSAGE]->(m)
                    """,
                    conv_id=conv_id,
                    msg_id=msg["msg_id"],
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg["timestamp"],
                    sequence=i
                )
            
            print(f"✅ 创建对话: 如何制定AI芯片发展战略? (ID={conv_id})")
            print(f"✅ 创建 {len(messages)} 条消息")
        
        # 5. 验证创建结果
        print("\n" + "=" * 80)
        print("验证创建结果")
        print("=" * 80)
        
        print(f"\n项目: {project.name}")
        print(f"  └─ 项目ID: {project.id}")
        print(f"  └─ 所属用户: {user.username} (ID={user.id})")
        
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Conversation {project_id: $project_id})
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                RETURN c.conversation_id as conv_id, c.title as title, count(m) as msg_count
                """,
                project_id=project.id
            ).single()
            
            if result:
                print(f"\n对话: {result['title']}")
                print(f"  └─ 对话ID: {result['conv_id']}")
                print(f"  └─ 消息数: {result['msg_count']}")
        
        print("\n✅ 测试数据创建成功！")
        
    finally:
        db.close()
        neo4j_driver.close()


def main():
    import sys
    
    print("\n" + "=" * 80)
    print("🔧 TechEyes 测试数据初始化工具")
    print("=" * 80)
    
    # 列出所有用户
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\n可用用户:")
        for user in users:
            projects_count = db.query(Project).filter(Project.user_id == user.id).count()
            print(f"  {user.id}. {user.username} - 已有{projects_count}个项目")
    finally:
        db.close()
    
    # 从命令行参数或用户输入获取用户名
    if len(sys.argv) > 1:
        username = sys.argv[1]
        print(f"\n选择用户: {username}")
    else:
        username = input("\n请输入要创建测试数据的用户名: ").strip()
    
    if username:
        create_test_data_for_user(username)
    else:
        print("❌ 用户名不能为空")


if __name__ == "__main__":
    main()
