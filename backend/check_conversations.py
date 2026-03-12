#!/usr/bin/env python3
"""检查项目对话记录"""

from database import get_db_context
from models.user import User
from models.project import ProjectConversation, Project

with get_db_context() as db:
    # 检查user_id=3是否存在
    user = db.query(User).filter(User.id == 3).first()
    if user:
        print(f'✅ 用户存在: id={user.id}, username={user.username}, email={user.email}')
    else:
        print('❌ user_id=3 不存在')
    
    print()
    
    # 查看所有对话记录
    conversations = db.query(ProjectConversation, Project.name, User.username).outerjoin(
        Project, ProjectConversation.project_id == Project.id
    ).outerjoin(
        User, ProjectConversation.user_id == User.id
    ).order_by(ProjectConversation.created_at.desc()).limit(20).all()
    
    print(f'数据库中所有对话记录（共{len(conversations)}条）:')
    for conv, project_name, username in conversations:
        deleted = '❌已删除' if conv.deleted_at else '✅正常'
        print(f'  ID={conv.id}, 用户={username}(user_id={conv.user_id}), 标题={conv.title}, 项目={project_name}, 状态={deleted}')
        print(f'      创建时间={conv.created_at}')
