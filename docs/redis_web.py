#!/usr/bin/env python3
"""
Redis 缓存 Web 可视化工具
访问: http://localhost:9001
"""
import redis
import json
from flask import Flask, render_template_string, request

app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redis 缓存管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .stat-label { font-size: 12px; color: #999; text-transform: uppercase; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 8px; }
        .cache-list { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .cache-item {
            padding: 20px;
            border-bottom: 1px solid #eee;
            transition: background 0.3s;
        }
        .cache-item:hover { background: #fafafa; }
        .cache-key {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #667eea;
            word-break: break-all;
            margin-bottom: 8px;
        }
        .cache-preview {
            background: #f9f9f9;
            padding: 10px;
            border-left: 3px solid #ddd;
            margin: 8px 0;
            border-radius: 4px;
            font-size: 13px;
            color: #666;
            max-height: 100px;
            overflow: auto;
        }
        .cache-meta {
            display: flex;
            gap: 15px;
            font-size: 12px;
            color: #999;
            margin-top: 8px;
        }
        .button {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }
        .button:hover { background: #764ba2; }
        .button.danger { background: #e74c3c; }
        .button.danger:hover { background: #c0392b; }
        .search-box {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }
        .search-box input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .search-box input:focus { outline: none; border-color: #667eea; }
        h1 { margin-bottom: 10px; }
        .subtitle { font-size: 14px; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Redis 缓存管理</h1>
            <p class="subtitle">实时查看和管理缓存数据</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">总键数</div>
                <div class="stat-value">{{ total_keys }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">总大小</div>
                <div class="stat-value">{{ total_size }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均大小</div>
                <div class="stat-value">{{ avg_size }}</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" placeholder="搜索缓存键..." id="search" onkeyup="filter()">
            <button class="button danger" onclick="clearAll()">清空所有缓存</button>
        </div>
        
        <div class="cache-list">
            {% for item in caches %}
            <div class="cache-item" class="cache-filter">
                <div class="cache-key">{{ item.key }}</div>
                <div class="cache-preview">{{ item.preview }}</div>
                <div class="cache-meta">
                    <span>📦 大小: {{ item.size }}</span>
                    <span>⏰ TTL: {{ item.ttl }}</span>
                    <button class="button" onclick="copy('{{ item.key }}')">复制</button>
                    <button class="button danger" onclick="deleteKey('{{ item.key }}')">删除</button>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        function filter() {
            const input = document.getElementById('search').value.toLowerCase();
            const items = document.querySelectorAll('[class="cache-filter"]');
            items.forEach(item => {
                const key = item.querySelector('.cache-key').textContent;
                item.style.display = key.toLowerCase().includes(input) ? '' : 'none';
            });
        }
        
        function copy(text) {
            navigator.clipboard.writeText(text);
            alert('已复制: ' + text);
        }
        
        function deleteKey(key) {
            if (confirm('确定删除此键吗? ' + key)) {
                fetch('/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({key: key})
                }).then(() => location.reload());
            }
        }
        
        function clearAll() {
            if (confirm('确定清空所有缓存吗？此操作不可撤销！')) {
                fetch('/clear', {method: 'POST'}).then(() => location.reload());
            }
        }
    </script>
</body>
</html>
"""

def human_size(size):
    if not size:
        return "0B"
    for unit in ['B', 'KB', 'MB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"

@app.route('/')
def index():
    try:
        r.ping()
    except:
        return "❌ Redis无法连接"
    
    keys = r.keys('*')
    total_size = sum(r.memory_usage(k) or 0 for k in keys)
    avg_size = total_size // max(len(keys), 1)
    
    caches = []
    for key in keys:
        val = r.get(key)
        size = r.memory_usage(key) or 0
        ttl = r.ttl(key)
        
        try:
            json_val = json.loads(val)
            if 'answer' in json_val:
                preview = json_val['answer'][:150]
            else:
                preview = json.dumps(json_val, ensure_ascii=False)[:150]
        except:
            preview = val[:150]
        
        caches.append({
            'key': key,
            'preview': preview + '...',
            'size': human_size(size),
            'ttl': '永久' if ttl < 0 else f'{ttl}秒'
        })
    
    return render_template_string(HTML_TEMPLATE, 
        caches=caches,
        total_keys=len(keys),
        total_size=human_size(total_size),
        avg_size=human_size(avg_size)
    )

@app.route('/delete', methods=['POST'])
def delete_key():
    data = request.json
    r.delete(data['key'])
    return {'status': 'ok'}

@app.route('/clear', methods=['POST'])
def clear_all():
    r.flushdb()
    return {'status': 'ok'}

if __name__ == '__main__':
    print("🚀 Redis Web 可视化工具启动中...")
    print("📍 访问地址: http://localhost:9001")
    print("⚠️  按 Ctrl+C 停止服务")
    app.run(host='0.0.0.0', port=9001, debug=True)
