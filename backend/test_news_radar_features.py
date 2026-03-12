#!/usr/bin/env python3
"""
新闻雷达新功能测试脚本

功能测试：
1. 获取热榜新闻
2. 强制刷新热榜
3. 手动刷新新闻
4. 删除新闻
"""

import requests
import json
from typing import Optional


# 配置
API_BASE = "http://localhost:8000/api"
TOKEN = None  # 如果需要认证，在这里填入JWT token


def get_headers():
    """获取请求头"""
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def test_get_hot_news(limit: int = 20, force_refresh: bool = False):
    """测试获取热榜新闻"""
    print("\n" + "="*60)
    print(f"📰 测试获取热榜新闻 (limit={limit}, force_refresh={force_refresh})")
    print("="*60)
    
    url = f"{API_BASE}/radar/hot"
    params = {"limit": limit}
    if force_refresh:
        params["force_refresh"] = "true"
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), timeout=30)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        
        print(f"✅ 成功获取 {len(items)} 条新闻")
        
        if items:
            print("\n前3条新闻：")
            for i, item in enumerate(items[:3], 1):
                print(f"\n{i}. {item.get('title', '无标题')}")
                print(f"   ID: {item.get('id')}")
                print(f"   URL: {item.get('url', 'N/A')}")
                print(f"   时间: {item.get('created_at', 'N/A')}")
                print(f"   摘要: {item.get('snippet', 'N/A')[:100]}...")
        else:
            print("⚠️  热榜为空，可能需要手动刷新")
        
        return items
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return None


def test_manual_refresh(limit: int = 20):
    """测试手动刷新热榜"""
    print("\n" + "="*60)
    print(f"🔄 测试手动刷新热榜 (limit={limit})")
    print("="*60)
    
    url = f"{API_BASE}/radar/refresh"
    params = {"limit": limit}
    
    try:
        response = requests.post(url, params=params, headers=get_headers(), timeout=60)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ {data.get('message', '刷新成功')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 刷新失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return False


def test_delete_news(news_id: str):
    """测试删除新闻"""
    print("\n" + "="*60)
    print(f"🗑️  测试删除新闻 (news_id={news_id})")
    print("="*60)
    
    url = f"{API_BASE}/radar/news/{news_id}"
    
    try:
        response = requests.delete(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ {data.get('message', '删除成功')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 删除失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   状态码: {e.response.status_code}")
            print(f"   响应内容: {e.response.text}")
        return False


def test_get_news_detail(news_id: str):
    """测试获取新闻详情"""
    print("\n" + "="*60)
    print(f"🔍 测试获取新闻详情 (news_id={news_id})")
    print("="*60)
    
    url = f"{API_BASE}/radar/news/{news_id}/detail"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        response.raise_for_status()
        
        data = response.json()
        news = data.get("news", {})
        graph = data.get("graph", {})
        
        print(f"✅ 新闻详情获取成功")
        print(f"\n标题: {news.get('title')}")
        print(f"URL: {news.get('url')}")
        print(f"实体数量: {len(graph.get('nodes', []))}")
        print(f"关系数量: {len(graph.get('edges', []))}")
        
        if graph.get('nodes'):
            print("\n相关实体（前5个）：")
            for i, node in enumerate(graph['nodes'][:5], 1):
                print(f"  {i}. {node.get('name')} ({node.get('type')})")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取详情失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return None


def test_search_news(query: str, limit: int = 10):
    """测试搜索新闻"""
    print("\n" + "="*60)
    print(f"🔍 测试搜索新闻 (query={query}, limit={limit})")
    print("="*60)
    
    url = f"{API_BASE}/radar/search"
    params = {"query": query, "limit": limit}
    
    try:
        response = requests.get(url, params=params, headers=get_headers(), timeout=20)
        response.raise_for_status()
        
        items = response.json()
        
        print(f"✅ 搜索到 {len(items)} 条相关新闻")
        
        if items:
            print(f"\n搜索结果（前3条）：")
            for i, item in enumerate(items[:3], 1):
                print(f"\n{i}. {item.get('title', '无标题')}")
                print(f"   时间: {item.get('created_at', 'N/A')}")
        
        return items
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 搜索失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   响应内容: {e.response.text}")
        return None


def main():
    """主测试流程"""
    print("\n" + "🎯"*30)
    print("新闻雷达功能测试")
    print("🎯"*30)
    
    # 测试1: 获取热榜（普通模式）
    items = test_get_hot_news(limit=20, force_refresh=False)
    
    # 测试2: 手动刷新热榜
    test_manual_refresh(limit=10)
    
    # 等待一下，让刷新完成
    print("\n⏳ 等待3秒让刷新完成...")
    import time
    time.sleep(3)
    
    # 测试3: 强制刷新获取最新新闻
    items = test_get_hot_news(limit=20, force_refresh=True)
    
    # 测试4: 如果有新闻，测试获取详情
    if items and len(items) > 0:
        news_id = items[0].get("id")
        if news_id:
            detail = test_get_news_detail(news_id)
            
            # 测试5: 搜索新闻
            test_search_news("AI", limit=5)
            
            # 测试6: 删除新闻（可选，谨慎使用）
            # 注意：这会真的删除数据！
            print("\n⚠️  删除测试已跳过（避免误删数据）")
            print("   如需测试删除功能，请手动调用：")
            print(f"   test_delete_news('{news_id}')")
            
            # 如果要测试删除，取消下面这行的注释
            # test_delete_news(news_id)
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    # 如果需要认证，请在这里登录获取token
    # 例如：
    # response = requests.post(f"{API_BASE}/auth/login", json={
    #     "username": "admin",
    #     "password": "admin123"
    # })
    # TOKEN = response.json()["access_token"]
    
    main()
