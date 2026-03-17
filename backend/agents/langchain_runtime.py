"""LangChain runtime primitives used by all agents in this project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


class LangChainLLM:
    """Thin wrapper around LangChain's chat model for project-wide consistency."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
        provider: str | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
    ) -> None:
        self.model = model
        self.provider = provider or "openai-compatible"
        self.base_url = base_url
        self.client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=timeout,
        )


class SimpleLangChainAgent:
    """Simple prompt-response agent based on LangChain chat models."""

    def __init__(self, name: str, llm: LangChainLLM, system_prompt: str = "") -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt or ""

    def run(self, prompt: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=prompt))
        response = self.llm.client.invoke(messages)
        return (response.content or "").strip()


@dataclass
class ToolRegistry:
    """Simple tool registry used for tool-aware prompt hints."""

    tools: List[object] = field(default_factory=list)

    def register_tool(self, tool: object) -> None:
        self.tools.append(tool)

    def list_tool_names(self) -> List[str]:
        return [getattr(t, "name", t.__class__.__name__) for t in self.tools]


class SearchTool:
    """Tool descriptor for compatibility with existing researcher flow."""

    name = "SearchTool"


class ReActLangChainAgent:
    """ReAct-style wrapper using LangChain with optional tool hints."""

    def __init__(
        self,
        name: str,
        llm: LangChainLLM,
        system_prompt: str = "",
        max_steps: int = 4,
    ) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt or ""
        self.max_steps = max_steps
        self.tool_registry: ToolRegistry | None = None
        self.enable_tool_calling = False

    def _build_user_prompt(self, prompt: str) -> str:
        if self.enable_tool_calling and self.tool_registry:
            tool_names = self.tool_registry.list_tool_names()
            if tool_names:
                return (
                    f"可用工具: {', '.join(tool_names)}\n"
                    "请在推理过程中考虑是否需要调用这些工具，并在输出中明确可执行结论。\n\n"
                    f"{prompt}"
                )
        return prompt

    def run(self, prompt: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))
        messages.append(HumanMessage(content=self._build_user_prompt(prompt)))
        response = self.llm.client.invoke(messages)
        return (response.content or "").strip()
