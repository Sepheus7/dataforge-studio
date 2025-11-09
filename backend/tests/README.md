# DataForge Studio Test Suite

## Overview

Comprehensive test suite covering core capabilities of DataForge Studio.

## Test Structure

- `test_core_capabilities.py` - Core functionality tests (schema inference, data generation, job management)
- `test_agents.py` - Agent-specific tests
- `test_api.py` - API endpoint tests
- `test_services.py` - Service layer tests
- `conftest.py` - Pytest fixtures and configuration

## Running Tests

```bash
# Activate conda environment
conda activate dataforge-studio

# Run all tests
pytest backend/tests/

# Run specific test file
pytest backend/tests/test_core_capabilities.py

# Run with coverage
pytest backend/tests/ --cov=app --cov-report=html

# Run with verbose output
pytest backend/tests/ -v

# Run specific test
pytest backend/tests/test_core_capabilities.py::TestSchemaInference::test_infer_schema_from_simple_prompt
```

## Test Coverage

### Core Capabilities
- ✅ Schema inference from natural language
- ✅ Multi-table schema with relationships
- ✅ Conversation memory and context
- ✅ Data generation with referential integrity
- ✅ Job lifecycle management
- ✅ API endpoint functionality
- ✅ Error handling and edge cases

### What's Tested
1. **Schema Inference**: Prompt analysis, entity extraction, relationship inference
2. **Data Generation**: Single/multi-table generation, row counts, seed reproducibility
3. **Job Management**: Creation, progress tracking, completion, failure handling
4. **API Endpoints**: Chat, generation, streaming, downloads
5. **Error Handling**: Invalid inputs, authentication, edge cases

## Test Environment

Tests use:
- Temporary directories for artifacts
- Mock/test API keys
- Disabled LangSmith tracing
- Local storage (no S3/Redis)

## Adding New Tests

When adding new features:
1. Add tests to appropriate test file
2. Use existing fixtures from `conftest.py`
3. Follow async test patterns for agent/service tests
4. Test both success and failure cases

