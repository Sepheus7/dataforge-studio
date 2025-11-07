"""Database schema parser"""

from typing import Dict, Any, List, Optional
import sqlparse
import re


class DBSchemaParser:
    """
    Parse database schema definitions (SQL DDL) to extract table structures.

    Converts DDL statements into DataForge schema format for generating
    synthetic data that matches database structures.
    """

    def __init__(self):
        """Initialize DB schema parser"""
        pass

    def parse_ddl(self, ddl_content: str) -> List[Dict[str, Any]]:
        """
        Parse SQL DDL to extract table schemas.

        Args:
            ddl_content: SQL DDL content

        Returns:
            List of table schemas
        """
        statements = sqlparse.split(ddl_content)
        schemas = []

        for statement in statements:
            parsed = sqlparse.parse(statement)[0]

            if self._is_create_table(parsed):
                schema = self._extract_table_schema(parsed)
                if schema:
                    schemas.append(schema)

        return schemas

    def _is_create_table(self, parsed_statement) -> bool:
        """Check if statement is CREATE TABLE"""
        tokens = [t for t in parsed_statement.tokens if not t.is_whitespace]
        if len(tokens) < 2:
            return False

        return (
            tokens[0].ttype is sqlparse.tokens.Keyword.DDL
            and tokens[0].value.upper() == "CREATE"
            and "TABLE" in tokens[1].value.upper()
        )

    def _extract_table_schema(self, parsed_statement) -> Optional[Dict[str, Any]]:
        """Extract table schema from CREATE TABLE statement"""
        statement_str = str(parsed_statement)

        # Extract table name
        match = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?", statement_str, re.IGNORECASE
        )
        if not match:
            return None

        table_name = match.group(1)

        # Extract column definitions
        columns = []
        primary_key = None

        # Find the part between parentheses
        match = re.search(r"\((.*)\)", statement_str, re.DOTALL)
        if not match:
            return None

        columns_str = match.group(1)

        # Split by commas (simplified parser)
        column_defs = [c.strip() for c in columns_str.split(",")]

        for col_def in column_defs:
            # Skip constraint definitions
            if re.match(
                r"(PRIMARY KEY|FOREIGN KEY|UNIQUE|CHECK|CONSTRAINT)", col_def, re.IGNORECASE
            ):
                if "PRIMARY KEY" in col_def.upper():
                    pk_match = re.search(r"PRIMARY\s+KEY\s*\(`?(\w+)`?\)", col_def, re.IGNORECASE)
                    if pk_match:
                        primary_key = pk_match.group(1)
                continue

            column = self._parse_column_definition(col_def)
            if column:
                if column.get("is_primary_key"):
                    primary_key = column["name"]
                columns.append(column)

        return {
            "name": table_name.lower(),
            "rows": 1000,
            "primary_key": primary_key,
            "columns": columns,
        }

    def _parse_column_definition(self, col_def: str) -> Optional[Dict[str, Any]]:
        """Parse a single column definition"""
        col_def = col_def.strip()

        # Extract column name (first word)
        parts = col_def.split()
        if len(parts) < 2:
            return None

        col_name = parts[0].strip("`")
        col_type_str = parts[1].upper()

        # Map SQL types to DataForge types
        column = {"name": col_name}

        if "INT" in col_type_str:
            column["type"] = "int"
        elif "FLOAT" in col_type_str or "DOUBLE" in col_type_str or "DECIMAL" in col_type_str:
            column["type"] = "float"
        elif "VARCHAR" in col_type_str or "TEXT" in col_type_str or "CHAR" in col_type_str:
            column["type"] = "string"
        elif "DATE" in col_type_str:
            if "DATETIME" in col_type_str or "TIMESTAMP" in col_type_str:
                column["type"] = "datetime"
            else:
                column["type"] = "date"
        elif "BOOL" in col_type_str:
            column["type"] = "boolean"
        elif "UUID" in col_type_str:
            column["type"] = "uuid"
        else:
            column["type"] = "string"

        # Check constraints
        col_def_upper = col_def.upper()
        column["unique"] = "UNIQUE" in col_def_upper
        column["null_ratio"] = 0.0 if "NOT NULL" in col_def_upper else 0.1
        column["is_primary_key"] = "PRIMARY KEY" in col_def_upper

        return column


# Global instance
_db_parser: Optional[DBSchemaParser] = None


def get_db_schema_parser() -> DBSchemaParser:
    """Get or create the global DB schema parser instance"""
    global _db_parser
    if _db_parser is None:
        _db_parser = DBSchemaParser()
    return _db_parser
