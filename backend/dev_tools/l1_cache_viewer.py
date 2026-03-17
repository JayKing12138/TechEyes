"""查看L1缓存内容"""
from services.cache_service import cache_service
from services.news_cache import news_cache

print("=== CacheService L1缓存 ===")
print(f"缓存条目数: {len(cache_service._l1_cache)}")
print("缓存键:")
for key in cache_service._l1_cache.keys():
    print(f"  - {key}")

print("\n=== NewsCache L1缓存 ===")
print(f"缓存条目数: {len(news_cache._l1_cache)}")
print("缓存键:")
for key in news_cache._l1_cache.keys():
    print(f"  - {key}")