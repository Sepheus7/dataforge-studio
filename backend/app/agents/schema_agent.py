"""Schema Inference Agent using LangGraph and Claude Haiku 4.5"""

from typing import Dict, Any, Optional, List
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
import json

from app.core.config import settings
from app.agents.tools import (
    analyze_prompt,
    suggest_columns,
    infer_relationships,
    validate_schema,
    normalize_schema,
)


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


class SchemaAgent:
    """
    Agent for inferring data schemas from natural language prompts.

    Uses LangGraph for state management and Claude Haiku 4.5 for reasoning.
    Integrates with LangSmith for tracing and evaluation.
    """

    def __init__(self):
        """Initialize the schema agent"""
        self.llm = self._create_llm()
        self.tools = [
            analyze_prompt,
            suggest_columns,
            infer_relationships,
            validate_schema,
            normalize_schema,
        ]
        self.graph = self._build_graph()

    def _create_llm(self) -> ChatBedrock:
        """Create LLM instance with Claude Haiku 4.5"""
        return ChatBedrock(
            model_id=settings.LLM_MODEL,
            region_name=settings.AWS_REGION,
            provider="anthropic",  # Required for Claude models
            model_kwargs={
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS,
            },
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

        return workflow.compile()

    async def _analyze_node(self, state: AgentState) -> AgentState:
        """Analyze the prompt using LLM reasoning to extract entities and relationships"""
        try:
            # Use LLM-powered analysis (no heuristics!)
            analysis = await analyze_prompt.ainvoke({"prompt": state["prompt"]})

            state["analysis"] = analysis
            reasoning = analysis.get("reasoning", "No reasoning provided")
            state["messages"].append(
                AIMessage(
                    content=f"Analysis complete: Found {len(analysis.get('entities', []))} entities. {reasoning}"
                )
            )
        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            import traceback

            print(traceback.format_exc())

        return state

    async def _draft_node(self, state: AgentState) -> AgentState:
        """Draft a schema based on analysis using LLM reasoning"""
        try:
            analysis = state.get("analysis")

            # Handle case where analysis failed
            if not analysis:
                state["error"] = "Analysis failed or returned None"
                return state

            entities = analysis.get("entities", [])
            size_hints = analysis.get("size_hints", {})
            domain = analysis.get("domain", "generic")
            prompt = state.get("prompt", "")

            # Create draft schema with LLM-powered column suggestion
            tables = []
            for entity in entities:
                # Get LLM-suggested columns (no heuristics!)
                columns = await suggest_columns.ainvoke(
                    {"entity": entity, "domain": domain, "context": prompt}
                )

                # Find primary key from suggested columns
                pk_col = next(
                    (c for c in columns if c.get("unique") and "id" in c["name"].lower()), None
                )
                primary_key = pk_col["name"] if pk_col else f"{entity.rstrip('s')}_id"

                table = {
                    "name": entity,
                    "rows": size_hints.get(entity, 1000),
                    "primary_key": primary_key,
                    "columns": columns,
                }
                tables.append(table)

            # LLM-powered relationship inference
            relationships = await infer_relationships.ainvoke(
                {"tables": entities, "domain": domain}
            )

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
            state["messages"].append(
                AIMessage(
                    content=f"Draft schema created with {len(tables)} tables using LLM reasoning"
                )
            )
        except Exception as e:
            state["error"] = f"Draft error: {str(e)}"
            import traceback

            print(traceback.format_exc())

        return state

    async def _validate_node(self, state: AgentState) -> AgentState:
        """Validate the draft schema"""
        try:
            draft = state.get("draft_schema")

            # Handle case where draft failed
            if not draft:
                state["error"] = "Draft schema failed or returned None"
                state["validation_result"] = {"valid": False, "errors": ["No draft schema"]}
                return state

            # Validate schema
            validation = validate_schema.invoke({"schema": draft})
            state["validation_result"] = validation

            if validation.get("valid"):
                state["messages"].append(AIMessage(content="Schema validation passed"))
            else:
                errors = validation.get("errors", [])
                state["messages"].append(
                    AIMessage(content=f"Schema validation failed: {', '.join(errors)}")
                )
        except Exception as e:
            state["error"] = f"Validation error: {str(e)}"

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
        try:
            # If there was an error, just pass through
            if state.get("error"):
                return state

            draft = state.get("draft_schema")
            if not draft:
                state["error"] = "No draft schema to finalize"
                return state

            # Normalize schema
            final_schema = normalize_schema.invoke({"schema": draft})
            state["final_schema"] = final_schema
            state["messages"].append(AIMessage(content="Schema finalized successfully"))
        except Exception as e:
            state["error"] = f"Finalization error: {str(e)}"

        return state

    async def infer_schema(
        self, prompt: str, size_hint: Optional[Dict[str, int]] = None, seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Infer a data schema from a natural language prompt.

        Args:
            prompt: Natural language description of desired data
            size_hint: Optional hints for table sizes
            seed: Random seed for reproducibility

        Returns:
            Inferred schema dictionary

        Raises:
            ValueError: If schema inference fails
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

        # Run the graph
        result = await self.graph.ainvoke(initial_state)

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
        _schema_agent = SchemaAgent()
    return _schema_agent
