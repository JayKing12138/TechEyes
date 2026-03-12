"""抓取真实新闻数据"""

import asyncio
from services.news_radar_service import news_radar_service

async def fetch_real_news():
    """抓取真实科技新闻"""
    print("开始抓取真实新闻...")
    
    queries = [
        "OpenAI GPT-5 最新消息",
        "特斯拉 FSD 自动驾驶",
        "苹果 Vision Pro",
        "英伟达 AI芯片",
        "微软 Copilot AI助手"
    ]
    
    for query in queries:
        print(f"\n正在搜索: {query}")
        try:
            result = await news_radar_service.fetch_and_ingest(
                query=query,
                max_items=5
            )
            print(f"✅ 成功抓取 {result['count']} 条新闻")
        except Exception as e:
            print(f"❌ 抓取失败: {e}")
    
    print("\n✅ 新闻抓取完成！")

if __name__ == "__main__":
    asyncio.run(fetch_real_news())
