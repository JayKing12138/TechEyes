#!/usr/bin/env python3
"""检查Redis持久化配置"""
import redis
import sys

try:
    # 连接Redis
    r = redis.from_url('redis://localhost:6379', decode_responses=True)
    
    print("=" * 80)
    print("Redis 持久化配置检查")
    print("=" * 80)
    
    # 检查连接
    if not r.ping():
        print("❌ Redis 未运行")
        sys.exit(1)
    
    print("\n✅ Redis 已连接\n")
    
    # RDB 持久化配置
    print("━" * 80)
    print("【RDB 快照持久化】")
    print("━" * 80)
    
    save_config = r.config_get('save')
    print(f"save 配置: {save_config.get('save', 'N/A')}")
    
    dbfilename = r.config_get('dbfilename')
    print(f"RDB 文件名: {dbfilename.get('dbfilename', 'N/A')}")
    
    rdb_dir = r.config_get('dir')
    print(f"RDB 目录: {rdb_dir.get('dir', 'N/A')}")
    
    rdbcompression = r.config_get('rdbcompression')
    print(f"RDB 压缩: {rdbcompression.get('rdbcompression', 'N/A')}")
    
    rdbchecksum = r.config_get('rdbchecksum')
    print(f"RDB 校验: {rdbchecksum.get('rdbchecksum', 'N/A')}")
    
    # AOF 持久化配置
    print("\n" + "━" * 80)
    print("【AOF 日志持久化】")
    print("━" * 80)
    
    appendonly = r.config_get('appendonly')
    is_aof_enabled = appendonly.get('appendonly', 'no') == 'yes'
    print(f"AOF 启用: {appendonly.get('appendonly', 'N/A')} {'✅' if is_aof_enabled else '❌'}")
    
    if is_aof_enabled:
        appendfilename = r.config_get('appendfilename')
        print(f"AOF 文件名: {appendfilename.get('appendfilename', 'N/A')}")
        
        appendfsync = r.config_get('appendfsync')
        print(f"AOF 同步策略: {appendfsync.get('appendfsync', 'N/A')}")
        
        auto_aof_rewrite_percentage = r.config_get('auto-aof-rewrite-percentage')
        print(f"AOF 自动重写百分比: {auto_aof_rewrite_percentage.get('auto-aof-rewrite-percentage', 'N/A')}%")
        
        auto_aof_rewrite_min_size = r.config_get('auto-aof-rewrite-min-size')
        print(f"AOF 自动重写最小大小: {auto_aof_rewrite_min_size.get('auto-aof-rewrite-min-size', 'N/A')}")
    else:
        print("  (AOF未启用，只使用RDB快照)")
    
    # 内存信息
    print("\n" + "━" * 80)
    print("【内存使用情况】")
    print("━" * 80)
    
    info = r.info('memory')
    used_memory = info.get('used_memory_human', 'N/A')
    used_memory_rss = info.get('used_memory_rss_human', 'N/A')
    used_memory_peak = info.get('used_memory_peak_human', 'N/A')
    
    print(f"已用内存: {used_memory}")
    print(f"RSS内存: {used_memory_rss}")
    print(f"峰值内存: {used_memory_peak}")
    
    # 持久化信息
    print("\n" + "━" * 80)
    print("【持久化状态】")
    print("━" * 80)
    
    persistence = r.info('persistence')
    
    if 'rdb_last_save_time' in persistence:
        import datetime
        last_save = datetime.datetime.fromtimestamp(persistence['rdb_last_save_time'])
        print(f"最后RDB保存: {last_save.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"RDB保存状态: {persistence.get('rdb_last_bgsave_status', 'N/A')}")
        print(f"RDB变更数: {persistence.get('rdb_changes_since_last_save', 'N/A')}")
    
    if is_aof_enabled and 'aof_enabled' in persistence:
        print(f"AOF启用状态: {persistence.get('aof_enabled', 'N/A')}")
        print(f"AOF重写状态: {persistence.get('aof_rewrite_in_progress', 'N/A')}")
        print(f"AOF最后状态: {persistence.get('aof_last_bgrewrite_status', 'N/A')}")
    
    # 键信息
    print("\n" + "━" * 80)
    print("【数据库信息】")
    print("━" * 80)
    
    db_info = r.info('keyspace')
    for db, stats in db_info.items():
        if db.startswith('db'):
            print(f"{db}: {stats}")
    
    total_keys = r.dbsize()
    print(f"总键数: {total_keys}")
    
    # 持久化建议
    print("\n" + "=" * 80)
    print("【持久化建议】")
    print("=" * 80)
    
    if not is_aof_enabled and save_config.get('save', '') == '':
        print("⚠️  当前Redis未启用任何持久化！")
        print("   - RDB 和 AOF 都未配置")
        print("   - 重启后数据将丢失")
        print("\n建议操作：")
        print("   方案1 (快速): 启用默认RDB")
        print("     redis-cli CONFIG SET save '900 1 300 10 60 10000'")
        print("   方案2 (高可靠): 启用AOF")
        print("     redis-cli CONFIG SET appendonly yes")
        print("     redis-cli CONFIG SET appendfsync everysec")
    elif not is_aof_enabled:
        print("✅ 当前使用 RDB 快照持久化")
        print(f"   - 配置: {save_config.get('save', 'N/A')}")
        print("   - 优点: 性能好，文件小")
        print("   - 缺点: 可能丢失最后几分钟数据")
        print("\n升级建议：")
        print("   启用AOF (更高可靠性):")
        print("     redis-cli CONFIG SET appendonly yes")
    else:
        print("✅ 当前使用 AOF 持久化")
        print(f"   - 同步策略: {appendfsync.get('appendfsync', 'N/A')}")
        print("   - 优点: 数据安全性高")
        print("   - 缺点: 性能略低，文件较大")
    
    print("\n" + "=" * 80)
    
except redis.ConnectionError:
    print("❌ 无法连接到 Redis (localhost:6379)")
    print("请先启动 Redis:")
    print("  brew services start redis")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
