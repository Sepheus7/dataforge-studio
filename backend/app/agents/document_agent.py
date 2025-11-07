"""Document Generation Agent - Fully LLM-driven, no templates"""

from typing import Dict, Any, Optional
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
import json

from app.core.config import settings
from app.agents.tools import llm_with_retry


class DocumentAgent:
    """
    Agent for generating synthetic documents using pure LLM creativity.

    No templates - the LLM generates complete documents based on:
    - Subject/topic
    - Style (formal, casual, technical, etc.)
    - Language
    - Format requirements

    Example: "Generate a German marketing article for Vanguard about sustainable investing"
    """

    def __init__(self):
        """Initialize the document agent"""
        self.llm = self._create_llm()

    def _create_llm(self) -> ChatBedrock:
        """Create LLM instance with higher token limit for document generation"""
        return ChatBedrock(
            model_id=settings.LLM_MODEL,
            region_name=settings.AWS_REGION,
            provider="anthropic",  # Required for Claude models
            model_kwargs={
                "temperature": 0.9,  # Higher for more creative generation
                "max_tokens": 8192,  # More tokens for longer documents
            },
        )

    async def generate_text_document(
        self,
        subject: str,
        style: str = "professional",
        language: str = "english",
        length: str = "medium",
        additional_requirements: Optional[str] = None,
    ) -> str:
        """
        Generate a complete text document using pure LLM creativity.

        NO TEMPLATES - the LLM writes the entire document based on its knowledge.

        Args:
            subject: Topic/subject of the document (e.g., "marketing article for Vanguard")
            style: Writing style (professional, casual, technical, academic, creative, etc.)
            language: Language to write in (english, german, french, spanish, etc.)
            length: Document length (short: ~500 words, medium: ~1000 words, long: ~2000 words)
            additional_requirements: Any other specific requirements

        Returns:
            Complete generated document as text

        Example:
            generate_text_document(
                subject="sustainable investing for Vanguard",
                style="marketing",
                language="german",
                length="medium"
            )
        """
        # Map length to word count guidance
        length_guidance = {
            "short": "approximately 500 words",
            "medium": "approximately 1000-1500 words",
            "long": "approximately 2000-2500 words",
        }
        target_length = length_guidance.get(length.lower(), "medium length")

        generation_prompt = f"""You are a professional writer. Create a complete, high-quality document with the following specifications:

**Subject:** {subject}
**Style:** {style}
**Language:** {language}
**Length:** {target_length}
**Additional Requirements:** {additional_requirements or 'None'}

Write a complete, polished document. Do NOT provide outlines or summaries - write the full document.

Guidelines:
- Use appropriate tone and vocabulary for the specified style
- Include relevant details, examples, and insights
- Structure the content logically with natural flow
- Write in the specified language ONLY
- Make it realistic and engaging
- Do not include meta-commentary (no "Here's the document:" or "This is a draft:")

Generate the complete document now:"""

        messages = [
            SystemMessage(
                content=f"You are an expert {style} writer who creates high-quality documents in {language}."
            ),
            HumanMessage(content=generation_prompt),
        ]

        response = await llm_with_retry(self.llm, messages)
        return response.content.strip()

    async def generate_structured_document(
        self, document_type: str, context: Dict[str, Any], language: str = "english"
    ) -> Dict[str, str]:
        """
        Generate a structured document (like invoice or contract) using LLM reasoning.

        The LLM determines the appropriate structure and content based on the document type
        and provided context, using its knowledge of standard document formats.

        Args:
            document_type: Type of document (invoice, contract, report, letter, etc.)
            context: Context data (company names, amounts, dates, etc.)
            language: Language to write in

        Returns:
            Dictionary with document sections as keys and generated content as values
        """
        context_str = json.dumps(context, indent=2)

        structured_prompt = f"""You are an expert at creating {document_type}s. Generate a complete, realistic {document_type} using this context:

{context_str}

Create a properly structured {document_type} in {language}. Use your knowledge of standard {document_type} formats to include all appropriate sections.

Return the document as a JSON object where keys are section names and values are the content for each section.

Example structure for an invoice:
{{
    "header": "Invoice content...",
    "billing_info": "Bill to:...",
    "items": "Line items...",
    "totals": "Subtotal:...",
    "payment_terms": "Payment terms..."
}}

Generate the complete {document_type} now as JSON:"""

        messages = [
            SystemMessage(
                content=f"You are a professional document creator specializing in {document_type}s."
            ),
            HumanMessage(content=structured_prompt),
        ]

        response = await llm_with_retry(self.llm, messages)

        # Parse JSON response
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback: return as single section
            return {"content": response.content}


# Global agent instance
_document_agent: Optional[DocumentAgent] = None


def get_document_agent() -> DocumentAgent:
    """Get or create the global document agent instance"""
    global _document_agent
    if _document_agent is None:
        _document_agent = DocumentAgent()
    return _document_agent
