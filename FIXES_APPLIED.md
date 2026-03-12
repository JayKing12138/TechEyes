# 修复清单 - 标题JSON和新闻链接显示问题

## 已应用的修复

### 1. 标题JSON污染修复 ✅
**问题**: 标题显示为 `{ "translation": "OpenClaw 爆发, Nvidia 跟进" }` 而不是干净的中文

**解决方案**:
- 文件: `backend/services/news_radar_service.py`
- 添加新方法: `_extract_clean_title()` 第1019行
  - 检测JSON格式并解析提取"translation"字段
  - 使用正则表达式从双引号中提取内容
  - 移除"翻译:"和"translation:"等前缀
  - 对太短或仍包含JSON字符的文本返回默认值"科技动态"

- 修改方法: `_format_and_translate_news_item()` 第980行
  - 在LLM翻译后**立即**调用_extract_clean_title清洗
  - 在return前再调用一次_extract_clean_title作为防线

**日志跟踪**: 输出日志 `[NewsRadar] 标题翻译: ... -> ...`

---

### 2. 新闻源链接显示修复 ✅
**问题**: 模板已添加但"参考新闻"链接不显示

**根本原因**: source_urls只在搜索档案路径保存，热门新闻路径没有保存到数据库

**解决方案**:
- 文件: `backend/services/news_radar_service.py`
- 修改方法: `_upsert_news_with_entities()` 第621行
  - 为热门新闻Neo4j保存查询添加: `n.source_urls = $source_urls`
  - 现在所有新闻（档案和热门）都保存source_urls

- 修改方法: `_serialize_news_record()` 第954行
  - JSON解析source_urls时添加日志: `反序列化source_urls：{count}条链接`
  - 解析失败时记录警告

- 修改方法: `_upsert_news_with_entities()` 第594行
  - 在保存前记录日志: `保存source_urls：{count}条链接`

**日志跟踪**:
- `[NewsRadar] 保存source_urls：N条链接 -> ...`
- `[NewsRadar] 反序列化source_urls：N条链接`

---

### 3. API响应验证 ✅
**文件**: `backend/api/news_radar_routes.py`

**修改**: 在`get_news_detail()`路由中添加日志
- `[NewsRadar API] 返回新闻{news_id}，包含{N}条source_urls`

---

### 4. 前端Vue语法修复 ✅
**文件**: `frontend/src/views/RadarNewsDetailPage.vue`

**修改**: 第369行，修复entityList计算属性的缺失闭括号
- 添加: `}`在entityList后面（第371行）
- 确保sourceUrls计算属性正确定义在第373行

**流程检查**:
- computed sourceUrls返回: `newsDetail.value.news.source_urls || []`
- Template v-if检查: `sourceUrls && sourceUrls.length > 0`
- v-for循环: `v-for="(source, index) in sourceUrls"`
- 访问属性: `source.title` 和 `source.url`

---

## 验证步骤

### 步骤1: 重启后端
```bash
cd /Users/cairongqing/Documents/techeyes/backend
python main.py
```

### 步骤2: 查看日志中是否出现
- 搜索新闻时: `[NewsRadar] 保存source_urls：`
- 获取新闻详情时: `[NewsRadar API] 返回新闻...包含...条source_urls`

### 步骤3: 测试界面
1. 进入新闻详情页
2. **验证标题**: 应该显示干净的中文，而不是 `{ "translation": "..." }`
3. **验证新闻链接**: 应该在"参考新闻"部分看到链接列表
4. 打开浏览器DevTools Network检查API响应中是否包含source_urls字段

### 步骤4: 浏览器控制台Debug
在`RadarNewsDetailPage.vue`mounted钩子中添加日志：
```typescript
onMounted(async () => {
  await loadNewsDetail()
  console.log('newsDetail:', newsDetail.value)  // 检查source_urls
  console.log('sourceUrls:', sourceUrls.value)  // 检查computed属性
})
```

---

## 技术细节

### 标题清洗流程
```
原始标题 (英文)
  ↓
_is_mostly_english() 检测
  ↓
entity_agent.run() LLM翻译
  ↓ 返回可能的JSON：{"translation": "翻译结果"}
_extract_clean_title() 清洗 ← 新增！
  ↓ 提取"translation"字段或正则提取
干净的中文标题
  ↓
_extract_clean_title() 再次清洗 ← 防线！
  ↓
返回给前端
```

### source_urls数据流
```
爬虫获取新闻
  ↓
source_urls: [{title, url}, ...]
  ↓
_upsert_news_with_entities()
  ↓
JSON.dumps() -> 保存为字符串到Neo4j
  ↓
get_news_detail()
  ↓
_serialize_news_record()
  ↓
JSON.parse() -> 转回数组
  ↓
返回API响应
  ↓
前端接收 newsDetail.news.source_urls
  ↓
computed sourceUrls
  ↓
v-for渲染链接
```

---

## 回滚计划（如需要）

如果有问题，可以：
1. 移除_extract_clean_title方法调用，使用原始标题
2. 临时禁用LLM标题翻译：`needs_translation = False`
3. 检查Neo4j是否有旧新闻数据，需要重新爬取才能有source_urls

---

## 相关文件修改摘要

| 文件 | 行号 | 修改内容 |
|------|------|---------|
| news_radar_service.py | 980 | _format_and_translate_news_item中添加_extract_clean_title调用 |
| news_radar_service.py | 1006 | 在return前再调用_extract_clean_title |
| news_radar_service.py | 1019-1060 | 新增_extract_clean_title方法 |
| news_radar_service.py | 594 | 添加source_urls保存日志 |
| news_radar_service.py | 610 | 添加source_urls到热门新闻Neo4j查询 |
| news_radar_service.py | 964-968 | 添加JSON解析日志 |
| news_radar_routes.py | 102-103 | 添加API响应日志 |
| RadarNewsDetailPage.vue | 371 | 修复entityList计算属性的缺失闭括号 |

