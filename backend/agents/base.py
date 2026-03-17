"""Agent 基类"""

from abc import ABC, abstractmethod
from agents.langchain_runtime import SimpleLangChainAgent, ReActLangChainAgent, LangChainLLM
from config import get_config

class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
        # 初始化 LLM
        config = get_config()
        self.llm = LangChainLLM(
            model=config.llm.model_id,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url if config.llm.base_url else None,
            provider=config.llm.provider
        )
    
    @abstractmethod
    async def execute(self, *args, **kwargs):
        """执行 Agent 的主要逻辑"""
        pass

class SimpleBaseAgent(BaseAgent):
    """简单 Agent 基类"""
    
    def __init__(self, name: str, description: str, system_prompt: str):
        super().__init__(name, description)
        
        self.agent = SimpleLangChainAgent(
            name=name,
            llm=self.llm,
            system_prompt=system_prompt
        )
    
    async def execute(self, query: str):
        """直接调用 Agent"""
        return self.agent.run(query)

class ReActBaseAgent(BaseAgent):
    """ReAct Agent 基类"""
    
    def __init__(self, name: str, description: str, system_prompt: str = None):
        super().__init__(name, description)
        
        self.agent = ReActLangChainAgent(
            name=name,
            llm=self.llm,
            system_prompt=system_prompt,
            max_steps=5
        )
    
    async def execute(self, query: str):
        """调用 ReAct Agent"""
        return self.agent.run(query)
