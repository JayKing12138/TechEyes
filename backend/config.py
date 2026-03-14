"""TechEyes 后端配置管理"""

import os
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 加载 .env 文件
load_dotenv()

class DatabaseConfig(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix='DATABASE_')
    
    url: str = Field(default='postgresql://postgres:1234@localhost:5432/techeyes', alias='DATABASE_URL')
    echo: bool = Field(default=False)
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=0)

class LLMConfig(BaseSettings):
    """LLM 配置"""
    model_config = SettingsConfigDict(env_prefix='LLM_')
    
    provider: str = Field(default='qwen')
    model_id: str = Field(default='qwen3.5-122b-a10b')
    api_key: str = Field(default='')
    base_url: str = Field(default='https://dashscope.aliyuncs.com/compatible-mode/v1')
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=4000)
    timeout: int = Field(default=60)

class SearchConfig(BaseSettings):
    """搜索工具配置"""
    serpapi_api_key: Optional[str] = Field(default=None, alias='SERPAPI_API_KEY')
    tavily_api_key: Optional[str] = Field(default=None, alias='TAVILY_API_KEY')
    tavily_include_raw_content: bool = Field(default=True, alias='TAVILY_INCLUDE_RAW_CONTENT')

class DocumentConfig(BaseSettings):
    """文档处理配置"""
    mineru_api_key: Optional[str] = Field(default=None, alias='MINERU_API_KEY')
    mineru_api_url: str = Field(default='https://mineru.net', alias='MINERU_API_URL')

class AppConfig(BaseSettings):
    """应用配置"""
    model_config = SettingsConfigDict(env_prefix='API_', extra='ignore')
    
    debug: bool = Field(default=True, alias='DEBUG')
    environment: str = Field(default='development', alias='ENVIRONMENT')
    host: str = Field(default='0.0.0.0')
    port: int = Field(default=8000)
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    
    # 存储路径
    storage_path: str = Field(default='./data/storage', alias='STORAGE_PATH')
    chroma_path: str = Field(default='./data/chroma', alias='CHROMA_PATH')
    log_path: str = Field(default='./logs', alias='LOG_PATH')
    upload_dir: str = Field(default='./data/uploads', alias='UPLOAD_DIR')
    
    @property
    def allowed_origins(self) -> List[str]:
        """获取允许的源列表，从环境变量或使用默认值"""
        origins_str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000')
        return [origin.strip() for origin in origins_str.split(',')]


class Neo4jConfig(BaseSettings):
    """图数据库（Neo4j）配置"""
    model_config = SettingsConfigDict(env_prefix='NEO4J_')

    uri: str = Field(default='bolt://localhost:7687', alias='NEO4J_URI')
    username: str = Field(default='neo4j', alias='NEO4J_USERNAME')
    password: str = Field(default='', alias='NEO4J_PASSWORD')
    database: str = Field(default='', alias='NEO4J_DATABASE')

class CacheConfig(BaseSettings):
    """缓存配置"""
    redis_url: str = Field(default='redis://localhost:6379', alias='REDIS_URL')
    cache_ttl: int = Field(default=86400, alias='CACHE_TTL')
    enable_semantic_cache: bool = Field(default=True, alias='ENABLE_SEMANTIC_CACHE')
    semantic_cache_threshold: float = Field(default=0.85, alias='SEMANTIC_CACHE_THRESHOLD')
    
    @property
    def ttl(self) -> int:
        """别名属性，保持向后兼容"""
        return self.cache_ttl

class AgentConfig(BaseSettings):
    """Agent 配置"""
    max_agent_steps: int = Field(default=10, alias='MAX_AGENT_STEPS')
    agent_timeout: int = Field(default=120, alias='AGENT_TIMEOUT')
    reflection_enabled: bool = Field(default=True, alias='REFLECTION_ENABLED')
    reflection_max_loops: int = Field(default=5, alias='REFLECTION_MAX_LOOPS')
    
    @property
    def max_steps(self) -> int:
        """别名属性"""
        return self.max_agent_steps
    
    @property
    def timeout(self) -> int:
        """别名属性"""
        return self.agent_timeout

    @property
    def max_reflection_loops(self) -> int:
        """反思循环最大次数（兼容命名）"""
        return self.reflection_max_loops


class RetrievalConfig(BaseSettings):
    """检索配置 - 多智能体RAG"""
    model_config = SettingsConfigDict(env_prefix='RETRIEVAL_')
    
    # 检索策略
    strategy: str = Field(default='hybrid', alias='RETRIEVAL_STRATEGY')  # simple/hybrid/multi_agent
    enable_reranker: bool = Field(default=True, alias='RETRIEVAL_ENABLE_RERANKER')
    enable_multi_agent: bool = Field(default=True, alias='RETRIEVAL_ENABLE_MULTI_AGENT')
    
    # BM25 和向量权重
    bm25_weight: float = Field(default=0.3, alias='RETRIEVAL_BM25_WEIGHT')
    vector_weight: float = Field(default=0.7, alias='RETRIEVAL_VECTOR_WEIGHT')
    
    # Reranker 模型
    reranker_model: str = Field(default='BAAI/bge-reranker-base', alias='RETRIEVAL_RERANKER_MODEL')
    
    # TopK 参数
    max_retrieval: int = Field(default=15, alias='RETRIEVAL_MAX_RETRIEVAL')  # 召回阶段
    final_top_k: int = Field(default=5, alias='RETRIEVAL_FINAL_TOP_K')  # 精排后
    max_per_doc: int = Field(default=2, alias='RETRIEVAL_MAX_PER_DOC')  # 单文档最多chunk数


# 全局配置实例
class Config:
    """全局配置"""
    database = DatabaseConfig()
    llm = LLMConfig()
    search = SearchConfig()
    document = DocumentConfig()
    app = AppConfig()
    cache = CacheConfig()
    agent = AgentConfig()
    retrieval = RetrievalConfig()
    graph = Neo4jConfig()

# 便利函数
def get_config() -> Config:
    """获取全局配置"""
    return Config()

# 创建必要的目录
def init_directories():
    """初始化必要的目录"""
    for directory in [
        Config.app.storage_path,
        Config.app.chroma_path,
        Config.app.log_path,
        Config.app.upload_dir
    ]:
        os.makedirs(directory, exist_ok=True)

if __name__ == '__main__':
    # 测试配置
    config = get_config()
    print("数据库配置:", config.database.url)
    print("LLM 提供商:", config.llm.provider)
    print("LLM 模型:", config.llm.model_id)
    print("SERPAPI:", "已配置" if config.search.serpapi_api_key else "未配置")
    print("TAVILY:", "已配置" if config.search.tavily_api_key else "未配置")
    print("MineRU:", "已配置" if config.document.mineru_api_key else "未配置")
    print("允许的源:", config.app.allowed_origins)
    print("检索策略:", config.retrieval.strategy)
    print("Reranker模型:", config.retrieval.reranker_model)

