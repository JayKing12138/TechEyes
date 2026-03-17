# 智能决策问答（项目对话）问题排查指南 🔍

## 📋 问题描述
用户登录后，访问项目详情页的"对话历史"标签页，显示列表为空。

## 🎯 可能的原因

### 原因1：用户从未创建过对话
**说明：** 对话需要用户主动发送第一条消息才会创建。

**排查方法：**
```bash
# 1. 登录系统
# 2. 进入项目详情页
# 3. 点击"分析对话"栏
# 4. 发送一条消息（例如："总结一下这个项目的核心内容"）
# 5. 刷新页面，查看"对话历史"标签页
```

**预期结果：** 发送消息后，对话列表应该出现一条新对话。

---

### 原因2：数据库迁移未执行
**说明：** `project_conversations` 表可能不存在或字段不匹配。

**排查方法：**
```bash
# 连接到PostgreSQL数据库
psql -U your_user -d techeyes

# 检查表是否存在
\dt project_conversations

# 查看表结构
\d project_conversations

# 查看是否有数据
SELECT COUNT(*) FROM project_conversations;
SELECT * FROM project_conversations ORDER BY created_at DESC LIMIT 5;
```

**预期结果：**
```sql
-- 表应该包含以下字段
      Column     |            Type             
-----------------+-----------------------------
 id              | bigint                     
 project_id      | bigint                     
 user_id         | integer                    
 title           | character varying(256)     
 created_at      | timestamp without time zone
 updated_at      | timestamp without time zone
 deleted_at      | timestamp without time zone
```

**如果表不存在，执行迁移：**
```bash
cd backend
# 使用Alembic迁移（如果项目使用Alembic）
alembic upgrade head

# 或者手动创建表（见下方SQL）
```

**手动创建表SQL：**
```sql
-- 创建 project_conversations 表
CREATE TABLE IF NOT EXISTS project_conversations (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(256),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE INDEX idx_project_conversations_project_id ON project_conversations(project_id);
CREATE INDEX idx_project_conversations_created_at ON project_conversations(created_at);

-- 创建 project_conversation_messages 表
CREATE TABLE IF NOT EXISTS project_conversation_messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES project_conversations(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    rag_used BOOLEAN DEFAULT FALSE,
    news_used BOOLEAN DEFAULT FALSE,
    doc_used BOOLEAN DEFAULT FALSE,
    doc_ids JSONB,
    chunk_ids JSONB,
    search_query TEXT,
    search_results_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_project_conversation_messages_conversation_id ON project_conversation_messages(conversation_id);
```

---

### 原因3：权限问题
**说明：** 用户只能看到自己创建的对话，可能是user_id不匹配。

**排查方法：**
```bash
# 1. 获取当前登录用户的user_id
# 在后端API中打印日志
# 或在数据库中查询

# 2. 检查是否有匹配的对话
SELECT c.*, p.name as project_name
FROM project_conversations c
JOIN projects p ON c.project_id = p.id
WHERE c.user_id = <当前用户ID>
  AND c.deleted_at IS NULL
ORDER BY c.updated_at DESC;
```

**预期结果：** 
- 如果返回空，说明该用户确实没有创建过对话
- 如果有数据但前端看不到，说明API调用有问题

---

### 原因4：前端API调用失败
**说明：** 前端调用 `/projects/{projectId}/conversations` 失败。

**排查方法：**
```bash
# 1. 打开浏览器开发者工具（F12）
# 2. 切换到 Network 标签页
# 3. 访问项目详情页
# 4. 查看是否有 /projects/{projectId}/conversations 的请求

# 5. 检查请求状态码
# - 200: 成功，但可能返回空数组
# - 401/403: 认证/权限问题
# - 404: 项目不存在
# - 500: 服务器错误
```

**使用curl测试API：**
```bash
# 获取token
TOKEN="your_jwt_token"

# 测试获取对话列表
curl -X GET \
  "http://localhost:8000/api/projects/1/conversations" \
  -H "Authorization: Bearer $TOKEN"

# 预期返回
{
  "conversations": []
}
# 或
{
  "conversations": [
    {
      "id": 1,
      "title": "总结项目内容",
      "created_at": "2024-01-xx...",
      ...
    }
  ]
}
```

---

### 原因5：deleted_at字段问题
**说明：** 所有对话都被标记为已删除（deleted_at不为NULL）。

**排查方法：**
```sql
-- 查看所有对话（包括已删除）
SELECT 
    id, 
    title, 
    created_at, 
    updated_at, 
    deleted_at
FROM project_conversations
ORDER BY created_at DESC;

-- 查看是否有未删除的对话
SELECT COUNT(*) 
FROM project_conversations 
WHERE deleted_at IS NULL;
```

**修复方法（如果误删除）：**
```sql
-- 恢复所有对话
UPDATE project_conversations
SET deleted_at = NULL
WHERE deleted_at IS NOT NULL;
```

---

## 🔧 完整测试流程

### Step 1: 检查数据库表
```bash
psql -U postgres -d techeyes -c "\d project_conversations"
```

### Step 2: 检查后端API
```bash
# 启动后端服务
cd backend
python main.py

# 查看日志
tail -f logs/app.log | grep -i conversation
```

### Step 3: 测试创建对话
```bash
# 使用curl发送测试消息
curl -X POST \
  "http://localhost:8000/api/projects/1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请总结一下这个项目的核心内容",
    "conversation_id": null
  }'
```

### Step 4: 查询对话列表
```bash
curl -X GET \
  "http://localhost:8000/api/projects/1/conversations" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Step 5: 前端调试
```javascript
// 在浏览器控制台执行
const conversations = await fetch('/api/projects/1/conversations', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
}).then(r => r.json())

console.log(conversations)
```

---

## 🐛 常见错误及解决方案

### 错误1: "relation \"project_conversations\" does not exist"
**原因：** 数据库表未创建
**解决：** 执行上面的"手动创建表SQL"

### 错误2: "column project_conversations.deleted_at does not exist"
**原因：** 表结构过旧，缺少 deleted_at 字段
**解决：**
```sql
ALTER TABLE project_conversations 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;
```

### 错误3: 401 Unauthorized
**原因：** Token过期或无效
**解决：** 
1. 重新登录获取新token
2. 检查 `Authorization: Bearer {token}` 格式是否正确

### 错误4: 404 Project Not Found
**原因：** project_id不存在或用户无权限
**解决：**
```sql
-- 检查项目是否存在
SELECT * FROM projects WHERE id = 1;

-- 检查用户权限
SELECT * FROM projects WHERE id = 1 AND user_id = <当前用户ID>;
```

---

## 📊 数据库诊断查询

```sql
-- 1. 查看所有项目的对话统计
SELECT 
    p.id,
    p.name,
    COUNT(c.id) as conversation_count,
    MAX(c.created_at) as last_conversation
FROM projects p
LEFT JOIN project_conversations c ON p.id = c.project_id AND c.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY conversation_count DESC;

-- 2. 查看用户的对话统计
SELECT 
    u.id,
    u.username,
    COUNT(c.id) as conversation_count
FROM users u
LEFT JOIN project_conversations c ON u.id = c.user_id AND c.deleted_at IS NULL
GROUP BY u.id, u.username
ORDER BY conversation_count DESC;

-- 3. 查看最近的对话活动
SELECT 
    c.id as conversation_id,
    c.title,
    p.name as project_name,
    u.username,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_time
FROM project_conversations c
JOIN projects p ON c.project_id = p.id
JOIN users u ON c.user_id = u.id
LEFT JOIN project_conversation_messages m ON c.id = m.conversation_id
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.title, p.name, u.username
ORDER BY last_message_time DESC
LIMIT 10;
```

---

## 🎯 快速修复建议

### 如果用户确实没创建过对话：
1. 引导用户在"分析对话"栏发送第一条消息
2. 系统会自动创建对话并显示在"对话历史"中

### 如果是数据库问题：
1. 执行上面的"手动创建表SQL"
2. 确保所有字段都存在
3. 运行数据库诊断查询检查数据

### 如果是权限问题：
1. 检查项目是否属于当前用户
2. 确保user_id正确
3. 查看后端日志确认权限验证逻辑

---

## 📝 临时调试代码

在 `backend/api/projects_routes.py` 的 `get_conversations` 函数中添加调试日志：

```python
@router.get("/{project_id}/conversations", response_model=dict)
async def get_conversations(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取项目对话列表"""
    service = ProjectService(db)
    
    # 验证项目权限
    project = service.get_project(project_id, user_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    conversations = service.get_conversations(project_id)
    
    # 🔍 添加调试日志
    logger.info(f"[DEBUG] 获取项目对话: project_id={project_id}, user_id={user_id}")
    logger.info(f"[DEBUG] 找到对话数量: {len(conversations)}")
    logger.info(f"[DEBUG] 对话列表: {[{'id': c.id, 'title': c.title, 'deleted_at': c.deleted_at} for c in conversations]}")
    
    return {
        "conversations": [ConversationResponse.from_orm(c) for c in conversations]
    }
```

重启后端服务，查看日志输出。

---

## ✅ 验证清单

- [ ] 数据库表 `project_conversations` 存在
- [ ] 表中有 `deleted_at` 字段
- [ ] 至少有一条对话记录（deleted_at为NULL）
- [ ] 后端API `/projects/{id}/conversations` 返回200
- [ ] 前端能正确调用API
- [ ] 用户有项目访问权限
- [ ] Token有效且未过期

---

## 🎉 预期正常流程

1. **用户登录** → 获取JWT token
2. **访问项目详情页** → 加载项目信息
3. **切换到"对话历史"标签** → 调用 GET `/projects/{id}/conversations`
4. **显示对话列表** → 如果为空，提示"开始一个新对话"
5. **发送第一条消息** → POST `/projects/{id}/chat`
6. **自动创建对话** → 对话列表立即更新
7. **查看对话内容** → 点击对话查看历史消息

如果某一步失败，参考上面的排查方法！
