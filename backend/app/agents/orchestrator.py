"""Multi-Agent Orchestrator for coordinating agent workflows"""

from typing import Dict, Any, Optional, Literal
from enum import Enum

from app.agents.schema_agent import get_schema_agent
from app.agents.document_agent import get_document_agent
from app.agents.replication_agent import get_replication_agent


class WorkflowType(str, Enum):
    """Types of agent workflows"""

    SCHEMA_GENERATION = "schema_generation"
    DOCUMENT_GENERATION = "document_generation"
    DATASET_REPLICATION = "dataset_replication"


class AgentOrchestrator:
    """
    Orchestrates multiple agents to handle complex workflows.

    Routes requests to appropriate agents and manages inter-agent communication.
    """

    def __init__(self):
        """Initialize the orchestrator"""
        self.schema_agent = get_schema_agent()
        self.document_agent = get_document_agent()
        self.replication_agent = get_replication_agent()

    async def route_request(
        self, workflow_type: WorkflowType, request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Route a request to the appropriate agent workflow.

        Args:
            workflow_type: Type of workflow to execute
            request: Request parameters

        Returns:
            Workflow results
        """
        if workflow_type == WorkflowType.SCHEMA_GENERATION:
            return await self._handle_schema_generation(request)
        elif workflow_type == WorkflowType.DOCUMENT_GENERATION:
            return await self._handle_document_generation(request)
        elif workflow_type == WorkflowType.DATASET_REPLICATION:
            return await self._handle_dataset_replication(request)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

    async def _handle_schema_generation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle schema generation workflow"""
        prompt = request.get("prompt")
        size_hint = request.get("size_hint")
        seed = request.get("seed")

        schema = await self.schema_agent.infer_schema(prompt=prompt, size_hint=size_hint, seed=seed)

        return {"workflow_type": "schema_generation", "schema": schema, "status": "success"}

    async def _handle_document_generation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document generation workflow"""
        document_type = request.get("document_type")
        requirements = request.get("requirements")

        structure = await self.document_agent.generate_document_structure(
            document_type=document_type, requirements=requirements
        )

        return {"workflow_type": "document_generation", "structure": structure, "status": "success"}

    async def _handle_dataset_replication(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dataset replication workflow"""
        df = request.get("dataframe")
        table_name = request.get("table_name")
        model_type = request.get("model_type", "gaussian_copula")

        # Analyze dataset
        analysis = await self.replication_agent.analyze_dataset_structure(
            df=df, table_name=table_name
        )

        # Get synthesis strategy
        strategy = await self.replication_agent.suggest_synthesis_strategy(
            analysis=analysis, model_type=model_type
        )

        return {
            "workflow_type": "dataset_replication",
            "analysis": analysis,
            "strategy": strategy,
            "status": "success",
        }

    def detect_workflow_type(self, request: Dict[str, Any]) -> WorkflowType:
        """
        Automatically detect the appropriate workflow type from request.

        Args:
            request: Request dictionary

        Returns:
            Detected workflow type
        """
        if "prompt" in request and "schema" not in request:
            return WorkflowType.SCHEMA_GENERATION
        elif "document_type" in request:
            return WorkflowType.DOCUMENT_GENERATION
        elif "dataframe" in request or "dataset_id" in request:
            return WorkflowType.DATASET_REPLICATION
        else:
            # Default to schema generation
            return WorkflowType.SCHEMA_GENERATION


# Global orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
