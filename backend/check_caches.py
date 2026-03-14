#!/usr/bin/env python3
"""检查三级缓存状态"""
import sys
from collections import OrderedDict

print("=" * 80)
print("三级缓存状态检查")
print("=" * 80)

# ============ L1缓存检查 ============
print("\n【L1缓存 - Python OrderedDict】")
print("  状态: ✅ 始终可用 (内存结构)")
print("  位置: backend/services/cache_service.py")
print("  配置: 最大300条, TTL 180秒")
print("  说明: 进程内存缓存，重启丢失")

# ============ L2缓存检查 ============
print("\n【L2缓存 - Redis】")
try:
    import redis
    r = redis.from_url('redis://localhost:6379', decode_responses=True)
    
    if not r.ping():
        print("  状态: ❌ Redis未响应")
        sys.exit(1)
    
    # 统计缓存键
    all_keys = r.keys('chat:v1:*')
    private_keys = [k for k in all_keys if ':private:' in k]
    public_keys = [k for k in all_keys if ':public:' in k]
    
    # 获取内存使用
    info = r.info('memory')
    memory_used = info.get('used_memory_human', 'N/A')
    
    print(f"  状态: ✅ 正常运行")
    print(f"  总键数: {r.dbsize()} (全部数据库)")
    print(f"  缓存键: {len(all_keys)} (chat:v1:*)")
    print(f"    ├─ private: {len(private_keys)}")
    print(f"    └─ public: {len(public_keys)}")
    print(f"  内存: {memory_used}")
    print(f"  连接: redis://localhost:6379")
    
    # 检查持久化配置
    save_config = r.config_get('save')
    aof_config = r.config_get('appendonly')
    print(f"  持久化: RDB={save_config.get('save', 'N/A')[:30]}...")
    print(f"           AOF={aof_config.get('appendonly', 'no')}")
    
except ImportError:
    print("  状态: ❌ redis模块未安装")
    print("  修复: pip install redis")
    sys.exit(1)
except redis.ConnectionError:
    print("  状态: ❌ 无法连接到Redis")
    print("  修复: brew services start redis")
    sys.exit(1)
except Exception as e:
    print(f"  状态: ❌ 错误 - {e}")
    sys.exit(1)

# ============ L3缓存检查 ============
print("\n【L3缓存 - PostgreSQL】")
try:
    from sqlalchemy import create_engine, text
    
    engine = create_engine('postgresql://postgres:1234@localhost:5432/techeyes')
    
    with engine.connect() as conn:
        # 检查表是否存在
        check_table = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'semantic_cache_index'
            )
        """)
        table_exists = conn.execute(check_table).scalar()
        
        if not table_exists:
            print("  状态: ❌ semantic_cache_index表不存在")
            sys.exit(1)
        
        # 统计记录
        count_query = text("SELECT COUNT(*) FROM semantic_cache_index")
        total = conn.execute(count_query).scalar()
        
        # 按scope统计
        scope_query = text("""
            SELECT scope, COUNT(*) as cnt 
            FROM semantic_cache_index 
            GROUP BY scope
        """)
        scope_stats = conn.execute(scope_query).fetchall()
        
        # 按owner_key统计
        owner_query = text("""
            SELECT owner_key, COUNT(*) as cnt 
            FROM semantic_cache_index 
            GROUP BY owner_key 
            ORDER BY cnt DESC 
            LIMIT 5
        """)
        owner_stats = conn.execute(owner_query).fetchall()
        
        print(f"  状态: ✅ 正常运行")
        print(f"  总记录: {total}")
        print(f"  按scope:")
        for scope, cnt in scope_stats:
            print(f"    ├─ {scope}: {cnt}")
        print(f"  Top用户 (owner_key):")
        for owner, cnt in owner_stats[:3]:
            print(f"    ├─ {owner}: {cnt}")
        print(f"  连接: postgresql://localhost:5432/techeyes")
        
except ImportError as e:
    print(f"  状态: ❌ 缺少模块 - {e}")
    sys.exit(1)
except Exception as e:
    print(f"  状态: ❌ 错误 - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============ 总结 ============
print("\n" + "=" * 80)
print("【总结】")
print("=" * 80)
print("✅ L1 (内存):     可用 - 进程内OrderedDict")
print("✅ L2 (Redis):    可用 - Homebrew 本地服务运行中")
print("✅ L3 (PostgreSQL): 可用 - 语义缓存索引正常")
print("\n🎉 三级缓存全部正常工作！")
print("=" * 80)
