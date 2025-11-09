"""Schema Inference Agent using LangGraph and Claude with Streaming"""

from typing import Dict, Any, Optional, List
from langchain_aws import ChatBedrockConverse  # New API with streaming!
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
import logging
import boto3
from botocore.config import Config

from app.core.config import settings
from app.agents.tools import (
    analyze_prompt,
    suggest_columns,
    infer_relationships,
    validate_schema,
    normalize_schema,
)
from app.utils.retry import exponential_backoff_retry

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for schema inference agent"""

    messages: List[Any]
    prompt: str
    analysis: Optional[Dict[str, Any]]
    draft_schema: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    final_schema: Optional[Dict[str, Any]]
    error: Optional[str]
    iteration: int
    job_id: Optional[str]  # For progress tracking


class SchemaAgent:
    """
    Agent for inferring data schemas from natural language prompts.

    Uses LangGraph for state management and Claude Haiku 4.5 for reasoning.
    Integrates with LangSmith for tracing and evaluation.
    """

    def __init__(self, job_manager=None):
        """Initialize the schema agent
        
        Args:
            job_manager: Optional JobManager instance for progress tracking
        """
        self.llm = self._create_llm()
        self.job_manager = job_manager
        self.tools = [
            analyze_prompt,
            suggest_columns,
            infer_relationships,
            validate_schema,
            normalize_schema,
        ]
        # Create checkpointer for conversation memory
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
    
    def _update_progress(self, job_id: Optional[str], progress: Optional[float], message: str):
        """Update job progress if job_manager is available"""
        if job_id and self.job_manager:
            # If progress is None, just send message without changing progress
            if progress is not None:
                self.job_manager.update_progress(job_id, progress, message)
                logger.info(f"Job {job_id}: {progress:.0%} - {message}")
            else:
                # Get current progress and send message
                current_job = self.job_manager._jobs.get(job_id)
                if current_job:
                    current_progress = current_job.get("progress", 0.0)
                    self.job_manager.update_progress(job_id, current_progress, message)
                    logger.info(f"Job {job_id}: (same progress) - {message}")

    def _create_llm(self) -> ChatBedrockConverse:
        """Create LLM instance with Claude Haiku 4.5"""
        # Create boto3 client with NO internal retries
        # We handle retries ourselves with exponential_backoff_retry
        boto_config = Config(
            retries={
                'max_attempts': 1,  # No retries at boto3 level
                'mode': 'standard'
            }
        )
        
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=boto_config
        )
        
        # Determine provider from model ID or use configured provider
        # OpenAI models: openai.*, Anthropic: anthropic.* or us.anthropic.*
        if settings.LLM_MODEL.startswith(("openai.", "openai/")):
            provider = "openai"
        elif settings.LLM_MODEL.startswith(("anthropic.", "us.anthropic.", "eu.anthropic.")):
            provider = "anthropic"
        elif settings.LLM_MODEL.startswith("arn:"):
            # For ARNs, check if it contains anthropic or openai
            if "anthropic" in settings.LLM_MODEL.lower():
                provider = "anthropic"
            elif "openai" in settings.LLM_MODEL.lower():
                provider = "openai"
            else:
                provider = settings.LLM_PROVIDER  # fallback to config
        else:
            provider = settings.LLM_PROVIDER  # fallback to config
        
        logger.info(f"🔧 Creating LLM with ChatBedrockConverse - model='{settings.LLM_MODEL}'")
        
        return ChatBedrockConverse(
            client=bedrock_client,  # Use our custom client
            model=settings.LLM_MODEL,
            region_name=settings.AWS_REGION,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            # Streaming is built-in - just call .stream() or .astream()
            # LangSmith will automatically trace if LANGCHAIN_TRACING_V2=true
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("draft", self._draft_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "draft")
        workflow.add_edge("draft", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._should_retry,
            {
                "retry": "draft",
                "finalize": "finalize",
            },
        )
        workflow.add_edge("finalize", END)

        return workflow.compile(checkpointer=self.checkpointer)

    async def _analyze_node(self, state: AgentState) -> AgentState:
        """Analyze the prompt using LLM reasoning to extract entities and relationships"""
        job_id = state.get("job_id")
        self._update_progress(job_id, 0.1, "🔍 Analyzing prompt...")
        
        try:
            # Use LLM-powered analysis with retry logic
            async def _analyze():
                return await analyze_prompt.ainvoke({"prompt": state["prompt"]})
            
            analysis = await exponential_backoff_retry(
                _analyze,
                max_retries=5,
                initial_delay=2.0
            )

            state["analysis"] = analysis
            reasoning = analysis.get("reasoning", "No reasoning provided")
            entities_count = len(analysis.get('entities', []))
            
            self._update_progress(
                job_id, 
                0.25, 
                f"✅ Analysis complete: Found {entities_count} entities"
            )
            
            state["messages"].append(
                AIMessage(
                    content=f"Analysis complete: Found {entities_count} entities. {reasoning}"
                )
            )
        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            logger.error(f"❌ Analysis failed: {str(e)}")
            import traceback
            print(traceback.format_exc())

        return state

    async def _draft_node(self, state: AgentState) -> AgentState:
        """Draft a schema based on analysis using LLM reasoning"""
        job_id = state.get("job_id")
        iteration = state.get("iteration", 0)
        # Progress updates handled by streaming loop
        
        try:
            analysis = state.get("analysis")

            # Handle case where analysis failed
            if not analysis:
                state["error"] = "Analysis failed or returned None"
                logger.error("❌ Draft failed: No analysis available")
                return state

            entities = analysis.get("entities", [])
            size_hints = analysis.get("size_hints", {})
            domain = analysis.get("domain", "generic")
            prompt = state.get("prompt", "")

            # Create draft schema with LLM-powered column suggestion
            tables = []
            for idx, entity in enumerate(entities):
                # Get LLM-suggested columns with retry logic
                async def _suggest():
                    return await suggest_columns.ainvoke(
                        {"entity": entity, "domain": domain, "context": prompt}
                    )
                
                columns = await exponential_backoff_retry(_suggest, max_retries=5, initial_delay=2.0)

                # Find primary key from suggested columns
                pk_col = next(
                    (c for c in columns if c.get("unique") and "id" in c["name"].lower()), None
                )
                primary_key = pk_col["name"] if pk_col else f"{entity.rstrip('s')}_id"

                table = {
                    "name": entity,
                    "rows": size_hints.get(entity, 100),
                    "primary_key": primary_key,
                    "columns": columns,
                }
                tables.append(table)

            # LLM-powered relationship inference with retry logic
            async def _infer():
                return await infer_relationships.ainvoke(
                    {"tables": entities, "domain": domain}
                )
            
            relationships = await exponential_backoff_retry(_infer, max_retries=5, initial_delay=2.0)

            # Add foreign keys to tables based on inferred relationships
            for rel in relationships:
                child_table = next((t for t in tables if t["name"] == rel.get("child_table")), None)
                if child_table:
                    if "foreign_keys" not in child_table:
                        child_table["foreign_keys"] = []

                    # Add FK column if not already present
                    fk_column = rel.get("foreign_key")
                    if not any(c["name"] == fk_column for c in child_table["columns"]):
                        child_table["columns"].append(
                            {
                                "name": fk_column,
                                "type": "uuid",
                                "description": f"Foreign key to {rel.get('parent_table')}",
                            }
                        )

                    child_table["foreign_keys"].append(
                        {
                            "column": fk_column,
                            "ref_table": rel.get("parent_table"),
                            "ref_column": rel.get("reference_key"),
                        }
                    )

            draft_schema = {"tables": tables}
            state["draft_schema"] = draft_schema
            
            logger.info(f"✅ Schema drafted with {len(tables)} tables")
            
            state["messages"].append(
                AIMessage(
                    content=f"Draft schema created with {len(tables)} tables using LLM reasoning"
                )
            )
        except Exception as e:
            state["error"] = f"Draft error: {str(e)}"
            logger.error(f"❌ Draft failed: {str(e)}")
            import traceback
            print(traceback.format_exc())

        return state

    async def _validate_node(self, state: AgentState) -> AgentState:
        """Validate the draft schema"""
        job_id = state.get("job_id")
        # Progress updates handled by streaming loop
        
        try:
            draft = state.get("draft_schema")

            # Handle case where draft failed
            if not draft:
                state["error"] = "Draft schema failed or returned None"
                state["validation_result"] = {"valid": False, "errors": ["No draft schema"]}
                return state

            # Validate schema with retry logic
            async def _validate():
                return validate_schema.invoke({"schema": draft})
            
            validation = await exponential_backoff_retry(_validate, max_retries=3, initial_delay=1.0)
            state["validation_result"] = validation

            if validation.get("valid"):
                logger.info("✅ Schema validation passed")
                state["messages"].append(AIMessage(content="Schema validation passed"))
            else:
                errors = validation.get("errors", [])
                logger.warning(f"⚠️ Validation issues found: {len(errors)} errors")
                state["messages"].append(
                    AIMessage(content=f"Schema validation failed: {', '.join(errors)}")
                )
        except Exception as e:
            state["error"] = f"Validation error: {str(e)}"
            logger.error(f"❌ Validation failed: {str(e)}")

        return state

    def _should_retry(self, state: AgentState) -> str:
        """Decide whether to retry or finalize"""
        # If there's an error, don't retry
        if state.get("error"):
            return "finalize"

        validation = state.get("validation_result")
        if not validation:
            return "finalize"

        iteration = state.get("iteration", 0)

        # Retry if invalid and under iteration limit
        if not validation.get("valid") and iteration < 3:
            state["iteration"] = iteration + 1
            return "retry"

        return "finalize"

    async def _finalize_node(self, state: AgentState) -> AgentState:
        """Finalize and normalize the schema"""
        job_id = state.get("job_id")
        # Progress updates handled by streaming loop
        
        try:
            # If there was an error, just pass through
            if state.get("error"):
                return state

            draft = state.get("draft_schema")
            if not draft:
                state["error"] = "No draft schema to finalize"
                logger.error("❌ Finalization failed: No draft schema")
                return state

            # Normalize schema with retry logic
            async def _normalize():
                return normalize_schema.invoke({"schema": draft})
            
            final_schema = await exponential_backoff_retry(_normalize, max_retries=3, initial_delay=1.0)
            state["final_schema"] = final_schema
            
            logger.info("✅ Schema finalized successfully")
            state["messages"].append(AIMessage(content="Schema finalized successfully"))
        except Exception as e:
            state["error"] = f"Finalization error: {str(e)}"

        return state

    async def infer_schema(
        self, 
        prompt: str, 
        size_hint: Optional[Dict[str, int]] = None, 
        seed: Optional[int] = None,
        job_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Infer a data schema from a natural language prompt.

        Args:
            prompt: Natural language description of desired data
            size_hint: Optional hints for table sizes
            seed: Random seed for reproducibility
            job_id: Optional job ID for progress tracking
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Inferred schema dictionary

        Raises:
            ValueError: If schema inference fails
        """
        # Configure thread_id for checkpointer
        thread_id_final = thread_id or f"thread_{job_id or 'default'}"
        config: RunnableConfig = {
            "configurable": {"thread_id": thread_id_final}
        }
        
        # Load previous state if thread_id exists (for conversation continuity)
        messages = [HumanMessage(content=prompt)]
        if thread_id:
            try:
                # Get the latest checkpoint state for this thread
                # get_tuple without checkpoint_id gets the latest checkpoint
                checkpoint_tuple = self.checkpointer.get_tuple(config)
                if checkpoint_tuple and checkpoint_tuple.checkpoint:
                    prev_state = checkpoint_tuple.checkpoint.get("channel_values", {})
                    if "messages" in prev_state and prev_state["messages"]:
                        # Prepend previous messages to maintain conversation context
                        prev_messages = prev_state["messages"]
                        messages = list(prev_messages) + messages
                        logger.info(
                            f"📚 Loaded {len(prev_messages)} previous messages "
                            f"from thread {thread_id_final}"
                        )
                        logger.debug(
                            f"📝 Previous messages: "
                            f"{[str(m)[:50] for m in prev_messages]}"
                        )
                    else:
                        logger.info(
                            f"🆕 Thread {thread_id_final} exists but no messages found"
                        )
                else:
                    logger.info(
                        f"🆕 New conversation thread {thread_id_final} "
                        f"- no previous checkpoints"
                    )
            except Exception as e:
                # No previous state - this is a new conversation
                logger.warning(
                    f"⚠️ Could not load conversation history for thread "
                    f"{thread_id_final}: {e}"
                )
                import traceback
                logger.debug(traceback.format_exc())
        
        # Initialize state with new prompt (and previous messages if loaded)
        initial_state = {
            "messages": messages,
            "prompt": prompt,
            "analysis": None,
            "draft_schema": None,
            "validation_result": None,
            "final_schema": None,
            "error": None,
            "iteration": 0,
            "job_id": job_id,  # Pass job_id for progress tracking
        }

        # Run the graph with detailed streaming for agent reasoning
        result = None
        
        # Use astream with stream_mode="updates" to capture node-by-node progress
        if self.job_manager and job_id:
            logger.info(f"🌊 Streaming agent reasoning with stream_mode='updates'")
            
            async for chunk in self.graph.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    logger.info(f"📍 Node executed: {node_name}, keys: {list(node_output.keys()) if isinstance(node_output, dict) else type(node_output)}")
                    
                    # Track progress based on node transitions
                    if node_name == "__start__":
                        self._update_progress(job_id, 0.05, "🚀 Starting schema inference...")
                    
                    elif node_name == "analyze":
                        # Extract meaningful info from analysis
                        if isinstance(node_output, dict) and "analysis" in node_output:
                            analysis = node_output["analysis"]
                            entities = analysis.get("entities", []) if isinstance(analysis, dict) else []
                            domain = analysis.get("domain", "generic") if isinstance(analysis, dict) else "generic"
                            self._update_progress(job_id, 0.20, f"🔍 Found {len(entities)} entities in {domain} domain")
                    
                    elif node_name == "draft":
                        if isinstance(node_output, dict) and "draft_schema" in node_output:
                            draft = node_output["draft_schema"]
                            if isinstance(draft, dict) and "tables" in draft:
                                tables = draft["tables"]
                                table_names = [t.get("name", "unknown") for t in tables] if tables else []
                                self._update_progress(job_id, 0.45, f"✍️ Drafted schema: {', '.join(table_names)}")
                    
                    elif node_name == "validate":
                        if isinstance(node_output, dict) and "validation_result" in node_output:
                            validation = node_output["validation_result"]
                            if isinstance(validation, dict):
                                if validation.get("valid"):
                                    self._update_progress(job_id, 0.70, "✅ Schema validation passed")
                                else:
                                    errors = len(validation.get("errors", []))
                                    self._update_progress(job_id, 0.70, f"⚠️ Found {errors} validation issues")
                    
                    elif node_name == "finalize":
                        if isinstance(node_output, dict) and "final_schema" in node_output:
                            final = node_output["final_schema"]
                            if isinstance(final, dict) and "tables" in final:
                                tables = final["tables"]
                                total_columns = sum(len(t.get("columns", [])) for t in tables)
                                self._update_progress(job_id, 0.90, f"✨ Finalized {len(tables)} tables with {total_columns} columns")
                        result = node_output
                    
                    # Store the latest output (accumulate state)
                    if node_output:
                        if result is None:
                            result = node_output
                        elif isinstance(result, dict) and isinstance(node_output, dict):
                            result.update(node_output)
                        else:
                            result = node_output
            
            logger.info(f"✅ Stream completed, final result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        else:
            # No streaming - regular invoke
            result = await self.graph.ainvoke(initial_state, config=config)

        # Check for errors
        if result.get("error"):
            raise ValueError(f"Schema inference failed: {result['error']}")

        final_schema = result.get("final_schema")
        if not final_schema:
            raise ValueError("Failed to generate schema")

        # Add seed if provided
        if seed is not None:
            final_schema["seed"] = seed

        # Override sizes with hints if provided
        if size_hint:
            for table in final_schema.get("tables", []):
                table_name = table["name"]
                if table_name in size_hint:
                    table["rows"] = size_hint[table_name]

        return final_schema

    def infer_schema_sync(
        self, prompt: str, size_hint: Optional[Dict[str, int]] = None, seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of infer_schema.

        Args:
            prompt: Natural language description
            size_hint: Optional size hints
            seed: Random seed

        Returns:
            Inferred schema
        """
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "prompt": prompt,
            "analysis": None,
            "draft_schema": None,
            "validation_result": None,
            "final_schema": None,
            "error": None,
            "iteration": 0,
        }

        # Run synchronously (simulate async for now)
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.graph.ainvoke(initial_state))
        finally:
            loop.close()

        if result.get("error"):
            raise ValueError(f"Schema inference failed: {result['error']}")

        final_schema = result.get("final_schema")
        if not final_schema:
            raise ValueError("Failed to generate schema")

        if seed is not None:
            final_schema["seed"] = seed

        if size_hint:
            for table in final_schema.get("tables", []):
                if table["name"] in size_hint:
                    table["rows"] = size_hint[table["name"]]

        return final_schema


# Global agent instance
_schema_agent: Optional[SchemaAgent] = None


def get_schema_agent() -> SchemaAgent:
    """Get or create the global schema agent instance"""
    global _schema_agent
    if _schema_agent is None:
        logger.info("🆕 Creating new SchemaAgent instance")
        _schema_agent = SchemaAgent()
    return _schema_agent


def reset_schema_agent():
    """Force reset the global schema agent (useful after config changes)"""
    global _schema_agent
    logger.info("♻️  Resetting SchemaAgent instance")
    _schema_agent = None
