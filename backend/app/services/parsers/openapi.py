"""OpenAPI specification parser"""

from typing import Dict, Any, List, Optional
import json
import yaml
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename


class OpenAPIParser:
    """
    Parse OpenAPI specifications to extract schemas for data generation.

    Converts OpenAPI schemas into DataForge schema format for generating
    test data that matches API specifications.
    """

    def __init__(self):
        """Initialize OpenAPI parser"""
        pass

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse an OpenAPI spec file.

        Args:
            file_path: Path to OpenAPI spec (JSON or YAML)

        Returns:
            Parsed specification
        """
        spec_dict, spec_url = read_from_filename(file_path)

        # Validate spec
        validate_spec(spec_dict)

        return spec_dict

    def extract_schemas(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract data schemas from OpenAPI spec.

        Args:
            spec: Parsed OpenAPI specification

        Returns:
            List of schemas suitable for data generation
        """
        schemas = []

        # Extract from components/schemas (OpenAPI 3.x)
        components = spec.get("components", {})
        component_schemas = components.get("schemas", {})

        for schema_name, schema_def in component_schemas.items():
            dataforge_schema = self._convert_schema(schema_name, schema_def)
            if dataforge_schema:
                schemas.append(dataforge_schema)

        # Extract from definitions (OpenAPI 2.x / Swagger)
        definitions = spec.get("definitions", {})
        for schema_name, schema_def in definitions.items():
            dataforge_schema = self._convert_schema(schema_name, schema_def)
            if dataforge_schema:
                schemas.append(dataforge_schema)

        return schemas

    def _convert_schema(
        self, schema_name: str, schema_def: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert OpenAPI schema to DataForge schema format.

        Args:
            schema_name: Name of the schema
            schema_def: OpenAPI schema definition

        Returns:
            DataForge schema or None if not convertible
        """
        if schema_def.get("type") != "object":
            return None

        properties = schema_def.get("properties", {})
        required_fields = set(schema_def.get("required", []))

        columns = []
        for prop_name, prop_def in properties.items():
            column = self._convert_property(prop_name, prop_def)
            column["unique"] = prop_name == "id"
            column["null_ratio"] = 0.0 if prop_name in required_fields else 0.1
            columns.append(column)

        return {
            "name": schema_name.lower(),
            "rows": 1000,  # Default
            "primary_key": "id" if "id" in properties else None,
            "columns": columns,
        }

    def _convert_property(self, prop_name: str, prop_def: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAPI property to DataForge column"""
        prop_type = prop_def.get("type", "string")
        prop_format = prop_def.get("format")

        column = {"name": prop_name}

        # Map OpenAPI types to DataForge types
        if prop_type == "integer":
            column["type"] = "int"
            if "minimum" in prop_def and "maximum" in prop_def:
                column["range"] = {"min": prop_def["minimum"], "max": prop_def["maximum"]}
        elif prop_type == "number":
            column["type"] = "float"
        elif prop_type == "string":
            if prop_format == "date":
                column["type"] = "date"
            elif prop_format == "date-time":
                column["type"] = "datetime"
            elif prop_format == "email":
                column["type"] = "email"
            elif prop_format == "uuid":
                column["type"] = "uuid"
            elif "enum" in prop_def:
                column["type"] = "categorical"
                column["categories"] = prop_def["enum"]
            else:
                column["type"] = "string"
        elif prop_type == "boolean":
            column["type"] = "boolean"
        else:
            column["type"] = "string"

        return column


# Global instance
_openapi_parser: Optional[OpenAPIParser] = None


def get_openapi_parser() -> OpenAPIParser:
    """Get or create the global OpenAPI parser instance"""
    global _openapi_parser
    if _openapi_parser is None:
        _openapi_parser = OpenAPIParser()
    return _openapi_parser
