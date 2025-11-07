"""Document parser for extracting structure from documents"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json


class DocumentParser:
    """
    Parse documents (PDF, DOCX, etc.) to extract structure.

    Useful for replicating document formats and extracting structured
    data from unstructured sources.
    """

    def __init__(self):
        """Initialize document parser"""
        pass

    def parse_json(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a JSON file to infer schema.

        Args:
            file_path: Path to JSON file

        Returns:
            Inferred schema
        """
        with open(file_path, "r") as f:
            data = json.load(f)

        # If it's a list, analyze the first item
        if isinstance(data, list) and len(data) > 0:
            return self._infer_from_dict(data[0], "data")
        elif isinstance(data, dict):
            return self._infer_from_dict(data, "data")
        else:
            return {"name": "data", "rows": 1000, "columns": []}

    def _infer_from_dict(self, data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Infer schema from a dictionary"""
        columns = []

        for key, value in data.items():
            column = {"name": key}

            if isinstance(value, bool):
                column["type"] = "boolean"
            elif isinstance(value, int):
                column["type"] = "int"
            elif isinstance(value, float):
                column["type"] = "float"
            elif isinstance(value, str):
                # Try to infer string subtype
                if "@" in value and "." in value:
                    column["type"] = "email"
                elif value.count("-") == 2 and len(value) == 10:
                    column["type"] = "date"
                else:
                    column["type"] = "string"
            elif isinstance(value, list):
                column["type"] = "categorical"
                column["categories"] = (
                    value if all(isinstance(v, str) for v in value) else ["A", "B", "C"]
                )
            else:
                column["type"] = "string"

            columns.append(column)

        return {"name": table_name.lower(), "rows": 1000, "columns": columns}

    def extract_tables_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """
        Extract multiple tables from nested JSON.

        Args:
            data: JSON data (dict or list)

        Returns:
            List of table schemas
        """
        tables = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    table = self._infer_from_dict(value[0], key)
                    tables.append(table)

        return tables


# Global instance
_document_parser: Optional[DocumentParser] = None


def get_document_parser() -> DocumentParser:
    """Get or create the global document parser instance"""
    global _document_parser
    if _document_parser is None:
        _document_parser = DocumentParser()
    return _document_parser
