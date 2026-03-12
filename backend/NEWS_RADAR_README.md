# 科技新闻雷达功能使用说明

## 🚀 快速开始

### 方式1：使用测试数据（推荐用于演示）

如果你想快速体验新闻雷达功能，可以使用测试数据：

```bash
cd backend

# 1. 确保已安装neo4j Python包
pip install neo4j

# 2. 启动Neo4j数据库（如果还没有）
# 使用Docker启动Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:latest

# 3. 更新.env文件中的Neo4j配置
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=password123

# 4. 运行测试数据脚本
python seed_test_news.py
```

### 方式2：使用真实新闻数据

如果你想获取真实的科技新闻：

1. **配置搜索API**（已在.env中配置）：
   - TAVILY_API_KEY（推荐）
   - SERPAPI_API_KEY

2. **启动后端服务**：
```bash
cd backend
python main.py
```

3. **访问新闻雷达页面**：
   - 打开浏览器访问：http://localhost:5173/radar
   - 系统会自动从搜索API获取最新科技新闻

## 📊 功能说明

### 1. 新闻热榜
- 显示最近最火的科技新闻
- 支持排名显示（前3名有特殊标记）
- 点击新闻卡片进入详情页

### 2. 新闻搜索
- 在搜索框输入关键词
- 支持标题和摘要搜索
- 实时返回搜索结果

### 3. 雷达档案
- 记录用户查看过的新闻
- 显示查看次数、分析次数
- 快速回访历史新闻

### 4. 新闻详情页
- **新闻内容**：完整的新闻文本
- **实体图谱**：可视化展示新闻中的实体关系
  - 点击实体节点可选中
  - 拖拽节点调整位置
  - 不同类型实体用不同颜色标识
- **按图索骥**：
  - 选择一个或多个实体
  - 输入自定义分析问题（可选）
  - 点击"开始分析"获取深度分析
- **雷达报告**：
  - 生成完整的分析报告
  - 包含用户历史、实体分析、相关实体

## 🎨 实体类型说明

| 类型 | 颜色 | 说明 |
|------|------|------|
| News | 青色 | 新闻节点 |
| company | 紫色 | 公司/企业 |
| person | 黄色 | 人物 |
| product | 绿色 | 产品 |
| technology | 红色 | 技术 |
| country | 灰色 | 国家/地区 |
| other | 白色 | 其他实体 |

## 🔧 API端点

### 获取热榜
```
GET /api/radar/hot?limit=20
```

### 搜索新闻
```
GET /api/radar/search?query=关键词&limit=20
```

### 获取新闻详情
```
GET /api/radar/news/{news_id}
```

### 按图索骥分析
```
POST /api/radar/analyze-entities
Body: {
  "entities": ["OpenAI", "GPT-5"],
  "question": "分析这两个实体的最新动向" // 可选
}
```

### 获取雷达档案
```
GET /api/radar/history?limit=50&offset=0
```

### 生成雷达报告
```
GET /api/radar/news/{news_id}/report
```

## 🐛 常见问题

### Q: 新闻热榜为空？
A: 
1. 检查Neo4j是否启动
2. 运行`python seed_test_news.py`添加测试数据
3. 或配置Tavily/SerpAPI密钥获取真实新闻

### Q: Neo4j连接失败？
A: 
1. 确保Neo4j服务已启动
2. 检查.env中的NEO4J_URI、NEO4J_USERNAME、NEO4J_PASSWORD
3. 确保端口7687未被占用

### Q: 图谱不显示？
A: 
1. 检查新闻是否有实体数据
2. 查看浏览器控制台是否有错误
3. 确保新闻详情API返回了graph数据

## 📝 测试数据说明

测试数据包含10条科技新闻：
1. OpenAI发布GPT-5
2. 特斯拉FSD V12推送
3. 苹果Vision Pro销量
4. DeepMind AlphaFold 3
5. 英伟达市值突破2万亿
6. 微软Copilot升级
7. Meta发布Llama 3
8. 亚马逊Titan芯片
9. 字节跳动豆包大模型
10. Anthropic融资

每条新闻包含：
- 标题、摘要、完整内容
- 5个左右的实体（公司、产品、技术、人物等）
- 实体重要性评分（0-1）

## 🎯 下一步

1. 启动后端服务：`cd backend && python main.py`
2. 启动前端服务：`cd frontend && npm run dev`
3. 访问：http://localhost:5173/radar
4. 体验完整的新闻雷达功能！
