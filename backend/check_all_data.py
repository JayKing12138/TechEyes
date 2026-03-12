"""检查所有用户、项目和对话数据"""
import sys
sys.path.insert(0, '/Users/cairongqing/Documents/techeyes/backend')

from database import SessionLocal
from models.user import User
from models.project import Project

def check_all_data():
    db = SessionLocal()
    try:
        print("\n" + "=" * 80)
        print("📊 数据库完整检查")
        print("=" * 80)
        
        # 检查用户
        print("\n1️⃣ 用户列表:")
        users = db.query(User).all()
        if not users:
            print("   ❌ 没有用户")
        else:
            for user in users:
                print(f"   • ID={user.id}, 用户名='{user.username}', 创建时间={user.created_at}")
        
        # 检查项目
        print("\n2️⃣ 项目列表:")
        projects = db.query(Project).all()
        if not projects:
            print("   ❌ 没有项目")
        else:
            for proj in projects:
                print(f"   • ID={proj.id}, 名称='{proj.name}', 所属用户ID={proj.user_id}")
        
        # 用户对应关系
        print("\n3️⃣ 用户 → 项目关系:")
        for user in users:
            user_projects = db.query(Project).filter(Project.user_id == user.id).all()
            print(f"\n   用户 '{user.username}' (ID={user.id}):")
            if not user_projects:
                print(f"      ❌ 无项目")
            else:
                for proj in user_projects:
                    print(f"      ├─ 项目 '{proj.name}' (ID={proj.id})")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    check_all_data()
