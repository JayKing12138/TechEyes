#!/usr/bin/env python3
"""搜索工具配置检查脚本"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from config import get_config
from tools.search_tools import TavilyTool, SERPAPITool
from loguru import logger

# 配置简单的日志输出
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

async def check_tavily():
    """检查 TAVILY 配置"""
    config = get_config()
    
    if not config.search.tavily_api_key:
        logger.warning("❌ TAVILY API Key 未配置")
        logger.info("   请在 .env 文件中设置: TAVILY_API_KEY=your_key")
        return False
    
    logger.info(f"✅ TAVILY API Key 已配置: {config.search.tavily_api_key[:10]}...")
    
    # 测试实际搜索
    logger.info("🔍 测试 TAVILY 搜索...")
    tool = TavilyTool()
    results = await tool.search("test query", max_results=1)
    
    if results:
        logger.success(f"✅ TAVILY 搜索成功: 返回 {len(results)} 条结果")
        return True
    else:
        logger.error("❌ TAVILY 搜索失败: 请检查 API Key 是否有效或配额是否用尽")
        return False

async def check_serpapi():
    """检查 SERPAPI 配置"""
    config = get_config()
    
    if not config.search.serpapi_api_key:
        logger.warning("❌ SERPAPI API Key 未配置")
        logger.info("   请在 .env 文件中设置: SERPAPI_API_KEY=your_key")
        return False
    
    logger.info(f"✅ SERPAPI API Key 已配置: {config.search.serpapi_api_key[:10]}...")
    
    # 测试实际搜索
    logger.info("🔍 测试 SERPAPI 搜索...")
    tool = SERPAPITool()
    results = await tool.search("test query", max_results=1)
    
    if results:
        logger.success(f"✅ SERPAPI 搜索成功: 返回 {len(results)} 条结果")
        return True
    else:
        logger.error("❌ SERPAPI 搜索失败: 请检查 API Key 是否有效或配额是否用尽")
        return False

async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("TechEyes 搜索工具配置检查")
    logger.info("=" * 60)
    
    tavily_ok = await check_tavily()
    print()
    serpapi_ok = await check_serpapi()
    
    print()
    logger.info("=" * 60)
    logger.info("检查结果汇总")
    logger.info("=" * 60)
    
    if tavily_ok or serpapi_ok:
        logger.success("✅ 至少有一个搜索工具可用，系统可以正常工作")
        if tavily_ok and serpapi_ok:
            logger.success("✅ 已配置主搜索（TAVILY）和备用搜索（SERPAPI）")
        elif tavily_ok:
            logger.warning("⚠️  仅配置了 TAVILY，建议同时配置 SERPAPI 作为备用")
        else:
            logger.warning("⚠️  仅配置了 SERPAPI，建议同时配置 TAVILY 提升搜索质量")
    else:
        logger.error("❌ 没有可用的搜索工具！")
        logger.error("   请至少配置 TAVILY 或 SERPAPI 其中一个")
        logger.info("")
        logger.info("📝 配置方法：")
        logger.info("   1. 在项目根目录创建或编辑 .env 文件")
        logger.info("   2. 添加以下配置：")
        logger.info("      TAVILY_API_KEY=your_tavily_api_key")
        logger.info("      SERPAPI_API_KEY=your_serpapi_api_key")
        logger.info("")
        logger.info("🔗 获取 API Key：")
        logger.info("   TAVILY:  https://tavily.com")
        logger.info("   SERPAPI: https://serpapi.com")
        
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
