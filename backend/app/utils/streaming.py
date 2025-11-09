"""Streaming utilities for LangChain callbacks"""

from typing import Any, Dict, List, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
import logging

logger = logging.getLogger(__name__)


class ReasoningStreamHandler(AsyncCallbackHandler):
    """
    Async callback handler to stream LLM reasoning to SSE.
    
    This captures:
    - LLM token-by-token output (streaming)
    - Tool/function calls
    - Agent steps
    """
    
    def __init__(self, job_id: str, event_publisher=None):
        """
        Initialize the streaming handler.
        
        Args:
            job_id: Job identifier for routing events
            event_publisher: Function to publish events (e.g., to SSE)
        """
        self.job_id = job_id
        self.event_publisher = event_publisher
        self.current_step = ""
    
    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts generating"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning",
                    "content": "🤔 Thinking...",
                    "step": self.current_step,
                }
            )
    
    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when LLM generates a new token (streaming)"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning_token",
                    "content": token,
                    "step": self.current_step,
                }
            )
    
    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes generating"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning_complete",
                    "content": "✅ Step complete",
                    "step": self.current_step,
                }
            )
    
    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error"""
        logger.error(f"LLM error in job {self.job_id}: {error}")
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning_error",
                    "content": f"❌ Error: {str(error)}",
                    "step": self.current_step,
                }
            )
    
    async def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Called when a tool/function is invoked"""
        tool_name = serialized.get("name", "tool")
        self.current_step = tool_name
        
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning",
                    "content": f"🔧 Using {tool_name}...",
                    "step": tool_name,
                }
            )
    
    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool/function completes"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning",
                    "content": f"✅ {self.current_step} complete",
                    "step": self.current_step,
                }
            )
    
    async def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a tool/function encounters an error"""
        logger.error(f"Tool error in job {self.job_id}: {error}")
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning_error",
                    "content": f"❌ Error in {self.current_step}: {str(error)}",
                    "step": self.current_step,
                }
            )
    
    async def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Called when agent takes an action"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning",
                    "content": f"🎯 Agent action: {action}",
                    "step": "agent_action",
                }
            )
    
    async def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        """Called when agent finishes"""
        if self.event_publisher:
            await self.event_publisher(
                self.job_id,
                {
                    "type": "reasoning",
                    "content": "🏁 Agent reasoning complete",
                    "step": "complete",
                }
            )

