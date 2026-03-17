"""Neo4j 图数据库客户端封装"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Callable

from loguru import logger
from neo4j import GraphDatabase, basic_auth, Driver, Session

from config import get_config


class Neo4jClient:
    """简单的 Neo4j 客户端封装，提供会话管理和通用查询方法。

    约定：
    - 所有 Radar/新闻相关的数据都存储在同一个 Neo4j 实例中
    - 数据库名称可选（Neo4j Aura / 企业版），默认使用默认数据库
    """

    _driver: Optional[Driver] = None

    def __init__(self) -> None:
        self.config = get_config().graph
        if not Neo4jClient._driver:
            self._init_driver()

    def _init_driver(self) -> None:
        uri = self.config.uri
        username = self.config.username
        password = self.config.password

        if not uri:
            raise RuntimeError("Neo4j 未配置 URI（NEO4J_URI）")

        logger.info(f"[Neo4j] 正在连接到 {uri} ...")
        Neo4jClient._driver = GraphDatabase.driver(
            uri,
            auth=basic_auth(username, password),
        )
        logger.info("[Neo4j] 连接初始化完成")

    @property
    def driver(self) -> Driver:
        if not Neo4jClient._driver:
            self._init_driver()
        assert Neo4jClient._driver is not None
        return Neo4jClient._driver

    def session(self) -> Session:
        """获取一个会话，必要时指定 database。"""
        db = (self.config.database or "").strip() or None
        if db:
            return self.driver.session(database=db)
        return self.driver.session()

    def run_query(
        self,
        cypher: str,
        parameters: Optional[Dict[str, Any]] = None,
        *,
        read_only: bool = True,
    ) -> Iterable[Dict[str, Any]]:
        """执行一个 Cypher 查询，并以字典形式返回记录。"""
        parameters = parameters or {}
        with self.session() as session:
            if read_only:
                result = session.execute_read(lambda tx: tx.run(cypher, **parameters).data())
            else:
                result = session.execute_write(lambda tx: tx.run(cypher, **parameters).data())
        return result

    def close(self) -> None:
        if Neo4jClient._driver:
            Neo4jClient._driver.close()
            Neo4jClient._driver = None


neo4j_client = Neo4jClient()

