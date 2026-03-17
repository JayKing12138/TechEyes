#!/usr/bin/env python3
"""Redis缓存可视化工具"""
import redis
import json
from typing import Any

class RedisViewer:
    def __init__(self, host='localhost', port=6379):
        self.r = redis.Redis(host=host, port=port, decode_responses=True)
    
    def view_all(self):
        """显示所有缓存"""
        try:
            self.r.ping()
            print(f"\n✅ Redis已连接 | 地址: localhost:6379")
            print(f"━" * 80)
            
            keys = self.r.keys('*')
            total_size = sum(self.r.memory_usage(k) or 0 for k in keys)
            
            print(f"总键数: {len(keys)} | 总大小: {self._human_size(total_size)}\n")
            
            # 显示所有键
            for i, key in enumerate(keys, 1):
                self._show_key(i, key)
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
    
    def _show_key(self, index, key):
        """显示单个键的信息"""
        val = self.r.get(key)
        size = self.r.memory_usage(key)
        ttl = self.r.ttl(key)
        
        print(f"{index}. 🔑 {key}")
        print(f"   大小: {self._human_size(size)} | TTL: {'永久' if ttl < 0 else f'{ttl}秒'}")
        
        try:
            json_val = json.loads(val)
            if 'answer' in json_val:
                preview = json_val['answer'][:120].replace('\n', ' ')
                print(f"   📝 {preview}...")
            else:
                preview = json.dumps(json_val, ensure_ascii=False)[:120]
                print(f"   📋 {preview}...")
        except:
            preview = val[:120]
            print(f"   📄 {preview}...")
        print()
    
    def view_key(self, pattern: str):
        """查看特定键"""
        keys = self.r.keys(f"*{pattern}*")
        
        if not keys:
            print(f"❌ 找不到包含 '{pattern}' 的键\n")
            return
        
        print(f"\n找到 {len(keys)} 个匹配的键:\n")
        for i, key in enumerate(keys, 1):
            self._show_key(i, key)
    
    def _human_size(self, size) -> str:
        if not size:
            return "0B"
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"
    
    def clear_cache(self, pattern=''):
        """清除缓存"""
        if pattern:
            keys = self.r.keys(f"*{pattern}*")
        else:
            keys = self.r.keys('*')
        
        if keys:
            deleted = self.r.delete(*keys)
            print(f"✅ 已清除 {deleted} 个缓存键")
        else:
            print(f"❌ 没有匹配的键")

if __name__ == "__main__":
    import sys
    viewer = RedisViewer()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'view' and len(sys.argv) > 2:
            viewer.view_key(sys.argv[2])
        elif cmd == 'clear':
            pattern = sys.argv[2] if len(sys.argv) > 2 else ''
            viewer.clear_cache(pattern)
    else:
        viewer.view_all()
