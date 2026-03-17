"""FastAPI 主应用"""

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import logging
from loguru import logger
import os
import time
import uuid

# 全局关闭 Chroma telemetry，避免 posthog 兼容性报错刷 ERROR。
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

from config import get_config, init_directories
from database import init_db, test_connection
import models

config = get_config()


def _is_placeholder_api_key(value: str) -> bool:
    key = (value or "").strip().lower()
    if not key:
        return True
    return (
        "your_" in key
        or "api_key_here" in key
        or "replace" in key
        or key in {"test", "demo", "placeholder"}
    )

# 初始化目录
init_directories()

# 配置日志
logger.remove()
os.makedirs(config.app.log_path, exist_ok=True)
logger.add(
    f"{config.app.log_path}/app.log",
    rotation="500 MB",
    level=config.app.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)

if config.app.debug:
    logger.add(
        lambda msg: print(msg, end=''),
        level=config.app.log_level,
        format="<level>{message}</level>"
    )


# 定时任务：每1小时刷新一次新闻热榜
async def scheduled_hot_news_refresh():
    """定时刷新新闻热榜（每1小时执行一次）"""
    from services.news_radar_service import news_radar_service
    
    while True:
        try:
            await asyncio.sleep(3600)  # 等待1小时（3600秒）
            logger.info("[定时任务] 开始刷新热榜新闻...")
            await news_radar_service.refresh_hot_news(limit=20)
            logger.info("[定时任务] 热榜刷新完成")
        except Exception as e:
            logger.error(f"[定时任务] 刷新热榜失败: {e}", exc_info=True)

# 启动和关闭事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info("=" * 80)
    logger.info("🚀 TechEyes Backend 正在启动...")
    logger.info("=" * 80)
    
    # 测试数据库连接
    if config.database.url:
        logger.info("📊 测试数据库连接...")
        if test_connection():
            logger.info("✅ 数据库连接成功")
            try:
                init_db()
                logger.info("✅ 数据库初始化成功")
            except Exception as e:
                logger.warning(f"⚠️  数据库初始化失败: {e}")
        else:
            logger.warning("⚠️  数据库连接失败")
    else:
        logger.warning("⚠️  数据库未配置（使用内存存储）")
    
    # 打印配置信息
    logger.info(f"📝 配置信息:")
    logger.info(f"  - 环境: {config.app.environment}")
    logger.info(f"  - 调试模式: {config.app.debug}")
    logger.info(f"  - LLM 提供商: {config.llm.provider}")
    logger.info(f"  - LLM 模型: {config.llm.model_id}")
    logger.info(f"  - API 地址: http://{config.app.host}:{config.app.port}")
    if _is_placeholder_api_key(config.llm.api_key):
        logger.warning("⚠️  LLM_API_KEY 仍为占位符或为空，LLM/Embedding 请求将返回 401")
    
    # 打印已配置的外部 API
    logger.info(f"🔧 已配置的工具:")
    if config.search.serpapi_api_key:
        logger.info(f"  ✅ SERPAPI - 网络搜索")
    if config.search.tavily_api_key:
        logger.info(f"  ✅ TAVILY - 高级搜索")
    if config.document.mineru_api_key:
        logger.info(f"  ✅ MineRU - 文档解析")
    
    logger.info("=" * 80)
    logger.info("✨ TechEyes Backend 已启动！")
    logger.info("=" * 80)
    
    # 启动定时刷新新闻任务
    refresh_task = asyncio.create_task(scheduled_hot_news_refresh())
    logger.info("📅 定时任务已启动：每1小时刷新一次新闻热榜")
    
    yield
    
    # 关闭事件
    logger.info("🛑 TechEyes Backend 正在关闭...")
    refresh_task.cancel()  # 取消定时任务

# 创建 FastAPI 应用
app = FastAPI(
    title="TechEyes API",
    version="1.0.0",
    description="Multi-Agent AI system for tech industry analysis with PostgreSQL backend",
    lifespan=lifespan
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.app.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    """请求级追踪日志：打印入口、出口、耗时、客户端信息"""
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())[:8]
    start = time.perf_counter()
    client_id = request.headers.get("x-client-id", "anonymous")
    method = request.method
    path = request.url.path

    logger.info(f"[REQ][{trace_id}] {method} {path} client={client_id}")

    try:
        response = await call_next(request)
        cost_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[RES][{trace_id}] {method} {path} status={response.status_code} cost={cost_ms:.1f}ms")
        response.headers["x-trace-id"] = trace_id
        return response
    except Exception as exc:
        cost_ms = (time.perf_counter() - start) * 1000
        logger.exception(f"[ERR][{trace_id}] {method} {path} cost={cost_ms:.1f}ms error={type(exc).__name__}: {exc}")
        raise

# 包含路由（后续添加）
from api.routes import router as api_router
from api.projects_routes import router as projects_router
from api.news_radar_routes import router as news_radar_router

app.include_router(api_router, prefix="/api")
app.include_router(projects_router)
app.include_router(news_radar_router)

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": config.app.environment,
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model_id
        }
    }

@app.get("/config")
async def get_app_config():
    """获取应用配置（不包含敏感信息）"""
    return {
        "environment": config.app.environment,
        "debug": config.app.debug,
        "llm_provider": config.llm.provider,
        "llm_model": config.llm.model_id,
        "tools": {
            "serpapi": bool(config.search.serpapi_api_key),
            "tavily": bool(config.search.tavily_api_key),
            "mineru": bool(config.document.mineru_api_key),
        },
        "agent_config": {
            "max_steps": config.agent.max_steps,
            "timeout": config.agent.timeout,
            "reflection_enabled": config.agent.reflection_enabled,
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.app.host,
        port=config.app.port,
        reload=config.app.debug,
        log_level=config.app.log_level.lower()
    )
