"""API routes for conversational chat with the agent"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from app.core.auth import verify_api_key
from app.models.requests import PromptRequest
from app.agents.schema_agent import get_schema_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat_with_agent(
    request: PromptRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Have a conversational chat with the agent.
    
    The agent can ask follow-up questions and clarify requirements
    before generating data. This does NOT trigger data generation.
    
    Args:
        request: Chat message with prompt and optional thread_id
        api_key: API key for authentication
    
    Returns:
        Agent's conversational response
    """
    try:
        schema_agent = get_schema_agent()
        
        # Configure thread_id for conversation continuity
        thread_id = request.thread_id or "default"
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id}
        }
        
        # Load conversation history
        messages = [HumanMessage(content=request.prompt)]
        if request.thread_id:
            try:
                checkpoint_tuple = schema_agent.checkpointer.get_tuple(config)
                if checkpoint_tuple and checkpoint_tuple.checkpoint:
                    prev_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                    if "messages" in prev_state and prev_state["messages"]:
                        prev_messages = prev_state["messages"]
                        messages = list(prev_messages) + messages
                        logger.info(
                            f"📚 Loaded {len(prev_messages)} previous messages "
                            f"from thread {thread_id}"
                        )
            except Exception as e:
                logger.debug(f"New conversation thread {thread_id}: {e}")
        
        # Add system prompt for conversational behavior
        from langchain_core.messages import SystemMessage
        system_prompt = """You are a helpful AI assistant for DataForge Studio, a synthetic data generation tool.

Your role is to:
1. Have a conversation with the user about their data needs
2. Ask clarifying questions to understand their requirements better
3. Only suggest generating data when you have enough information
4. Be conversational and helpful, not immediately jump to generation

When the user asks about generating data:
- Ask follow-up questions about:
  * What entities/tables they need
  * How many rows they want
  * What relationships exist between entities
  * Any specific requirements or constraints
- Only when you have enough details, suggest proceeding with generation
- Use phrases like "Would you like me to generate this data now?" or "Should I proceed with generating the dataset?"

Be friendly, helpful, and conversational. Don't immediately start generating - have a conversation first."""
        
        # Prepend system message if this is a new conversation
        if len(messages) == 1:  # Only the user message
            messages = [SystemMessage(content=system_prompt)] + messages
        
        # Use LLM directly for conversational response
        response = await schema_agent.llm.ainvoke(messages)
        
        # Extract response content
        if hasattr(response, 'content'):
            if isinstance(response.content, list):
                # Handle list of content blocks
                content = "".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in response.content
                )
            else:
                content = str(response.content)
        else:
            content = str(response)
        
        # Save conversation to checkpointer for memory
        # Add the AI response to messages
        messages.append(AIMessage(content=content))
        
        # Save conversation state using checkpointer
        # We'll create a minimal state that can be saved
        try:
            from langgraph.checkpoint.base import Checkpoint
            
            # Get existing checkpoint or create new
            checkpoint_tuple = schema_agent.checkpointer.get_tuple(config)
            existing_messages = []
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                prev_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                if "messages" in prev_state:
                    existing_messages = list(prev_state["messages"])
            
            # Combine existing messages with new ones (avoid duplicates)
            all_messages = existing_messages + messages[-2:]  # Just add user + AI message
            
            # Create checkpoint with updated messages
            checkpoint = Checkpoint(
                v=1,
                channel_values={"messages": all_messages},
                channel_versions={},
                versions_seen={},
            )
            
            # Save checkpoint
            await schema_agent.checkpointer.aput(config, checkpoint, {}, {})
            logger.debug(f"💾 Saved conversation to thread {thread_id}")
        except Exception as e:
            logger.warning(f"Could not save conversation state: {e}")
            # Continue even if saving fails - conversation will still work
        
        return {
            "response": content,
            "thread_id": thread_id,
            "needs_clarification": _check_if_needs_clarification(content),
        }
    
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _check_if_needs_clarification(response: str) -> bool:
    """Check if the agent's response indicates it needs more information"""
    clarification_keywords = [
        "need more", "could you", "can you", "please provide",
        "what", "which", "how many", "clarify", "specify"
    ]
    response_lower = response.lower()
    return any(keyword in response_lower for keyword in clarification_keywords)

