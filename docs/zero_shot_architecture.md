# Zero-Shot Architecture

## Overview

DataForge Studio uses a **pure LLM reasoning approach** with **zero heuristics** and **no hardcoded templates**. This makes the system highly flexible and able to handle complex, novel requests without pre-programming specific patterns.

## Design Principles

### 1. **No Heuristics**

- Traditional synthetic data systems use pattern matching and predefined rules
- DataForge Studio uses Claude Haiku 4.5's reasoning capabilities to understand intent
- The LLM applies its knowledge of data modeling and document structures

### 2. **No Templates**

- No hardcoded document templates (invoices, reports, etc.)
- No predefined schema patterns (customer→order relationships)
- The LLM generates structures based on its training and understanding

### 3. **Pure Reasoning**

- Every decision flows from LLM analysis of the user's request
- Column types, relationships, document sections - all inferred by the LLM
- Fallback logic is minimal and only for error handling

## Architecture Components

### Schema Generation Agent

The schema generation flow is purely LLM-driven:

1. **Prompt Analysis** (`analyze_prompt` tool)
   - LLM reads the user prompt
   - Reasons about what entities (tables) are needed
   - Determines business domain context
   - Infers relationships between entities
   - **NO pattern matching on keywords**

2. **Column Suggestion** (`suggest_columns` tool)
   - For each entity, LLM determines appropriate columns
   - Uses knowledge of typical data structures
   - Considers domain context (ecommerce vs healthcare)
   - **NO column templates**

3. **Relationship Inference** (`infer_relationships` tool)
   - LLM analyzes table names and domain
   - Reasons about logical relationships (orders → customers)
   - Determines foreign key columns
   - **NO hardcoded relationship patterns**

4. **Validation & Finalization**
   - Schema validated for integrity
   - Data generation proceeds with inferred structure

### Document Generation Agent

Document generation is completely LLM-creative:

1. **Text Documents** (`generate_text_document`)

   ```python
   # Example: Marketing article in German about sustainable investing
   document = await agent.generate_text_document(
       subject="sustainable investing for Vanguard",
       style="marketing", 
       language="german",
       length="medium"
   )
   ```

   - LLM writes the complete document from scratch
   - No templates, no fill-in-the-blank
   - Pure creative generation based on style and subject

2. **Structured Documents** (`generate_structured_document`)

   ```python
   # Example: Invoice
   document = await agent.generate_structured_document(
       document_type="invoice",
       context={"company": "Acme Corp", "amount": 1500},
       language="english"
   )
   ```

   - LLM determines appropriate structure for document type
   - Generates realistic content for each section
   - **NO invoice templates or predefined formats**

## Benefits

### 1. **Extreme Flexibility**

- Can handle any prompt, no matter how unusual
- "Create a healthcare patient database with IoT device integration"
- "Generate a Japanese legal contract for software licensing"
- No need to pre-program these scenarios

### 2. **Natural Language Understanding**

- User can describe requirements conversationally
- "I need customer data with orders that link to products"
- System understands the intent and relationships

### 3. **Domain Adaptation**

- LLM applies domain knowledge automatically
- Healthcare databases get HIPAA-relevant fields
- Finance databases get compliance-aware structures
- No manual domain configuration needed

### 4. **Continuous Improvement**

- As LLMs improve, the system gets better
- No code changes needed to leverage new model capabilities
- Future models bring better reasoning automatically

### 5. **Reduced Maintenance**

- No template library to maintain
- No heuristic rules to update
- No pattern matching logic to fix

## Trade-offs

### Advantages

- ✅ Handles novel requests gracefully
- ✅ Very flexible and adaptable
- ✅ Natural language interface
- ✅ Low maintenance burden

### Considerations

- ⚠️ Higher latency (LLM inference time)
- ⚠️ Requires good prompting for best results
- ⚠️ Outputs may vary slightly between runs
- ⚠️ Dependent on LLM capability and availability

## Implementation Details

### Async Tool Execution

All agent tools are async:

```python
@tool
async def analyze_prompt(prompt: str) -> Dict[str, Any]:
    llm = get_llm()
    response = await llm.ainvoke(messages)
    return json.loads(response.content)
```

### JSON Response Parsing

LLM outputs are parsed from JSON:

```python
# Handle markdown code blocks
content = response.content
if "```json" in content:
    content = content.split("```json")[1].split("```")[0]

result = json.loads(content.strip())
```

### Error Handling

Minimal fallback logic:

```python
try:
    return json.loads(response.content)
except json.JSONDecodeError:
    # Minimal fallback, not a heuristic
    return {"entities": ["data"], "relationships": []}
```

## Future Enhancements

1. **Multi-Agent Orchestration**
   - Specialized agents for different domains
   - Agents collaborate on complex requests

2. **Tool Calling Optimization**
   - Parallel tool execution where possible
   - Caching of repeated analyses

3. **Human-in-the-Loop**
   - Optional review step before generation
   - Interactive schema refinement

4. **Learning from Feedback**
   - Store successful patterns
   - Use few-shot learning for better results

## Testing

See `backend/test_zero_shot.py` for validation tests:

```bash
conda activate dataforge-studio
cd backend
python test_zero_shot.py
```

This validates that the system truly uses zero-shot reasoning without falling back to heuristics.
