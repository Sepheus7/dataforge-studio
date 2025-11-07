"""Dataset Replication Agent for synthetic data generation from existing datasets"""

from typing import Dict, Any, Optional, List
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
import pandas as pd

from app.core.config import settings


class ReplicationAgent:
    """
    Agent for analyzing and replicating datasets with PII replacement.

    Uses SDV for synthesis and spacy for PII detection.
    """

    def __init__(self):
        """Initialize the replication agent"""
        self.llm = self._create_llm()

    def _create_llm(self) -> ChatBedrock:
        """Create LLM instance"""
        return ChatBedrock(
            model_id=settings.LLM_MODEL,
            region_name=settings.AWS_REGION,
            model_kwargs={
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "max_tokens": 4096,
            },
        )

    async def analyze_dataset_structure(self, df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """
        Analyze a dataset to understand its structure and patterns.

        Args:
            df: Pandas DataFrame to analyze
            table_name: Name of the table

        Returns:
            Analysis results including column types, distributions, and patterns
        """
        analysis = {
            "table_name": table_name,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "columns": [],
            "missing_values": {},
            "correlations": [],
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "unique_count": df[col].nunique(),
                "null_count": df[col].isnull().sum(),
                "null_percentage": df[col].isnull().sum() / len(df) * 100,
            }

            # Detect data type
            if df[col].dtype in ["int64", "float64"]:
                col_info["data_type"] = "numeric"
                col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                col_info["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
            elif df[col].dtype == "object":
                if df[col].nunique() < 20:  # Categorical threshold
                    col_info["data_type"] = "categorical"
                    col_info["categories"] = df[col].value_counts().head(10).to_dict()
                else:
                    col_info["data_type"] = "string"
            else:
                col_info["data_type"] = "other"

            analysis["columns"].append(col_info)

        return analysis

    async def detect_relationships(self, tables: Dict[str, pd.DataFrame]) -> List[Dict[str, str]]:
        """
        Detect potential foreign key relationships between tables.

        Args:
            tables: Dictionary of table_name -> DataFrame

        Returns:
            List of detected relationships
        """
        relationships = []

        table_names = list(tables.keys())

        # Check for common column names that might be foreign keys
        for i, table1_name in enumerate(table_names):
            df1 = tables[table1_name]
            for table2_name in table_names[i + 1 :]:
                df2 = tables[table2_name]

                # Find common columns
                common_cols = set(df1.columns) & set(df2.columns)

                for col in common_cols:
                    if col.endswith("_id") or col == "id":
                        # Check if values in one are subset of the other
                        vals1 = set(df1[col].dropna().unique())
                        vals2 = set(df2[col].dropna().unique())

                        if vals1.issubset(vals2):
                            relationships.append(
                                {
                                    "child_table": table1_name,
                                    "parent_table": table2_name,
                                    "foreign_key": col,
                                    "confidence": "high",
                                }
                            )
                        elif vals2.issubset(vals1):
                            relationships.append(
                                {
                                    "child_table": table2_name,
                                    "parent_table": table1_name,
                                    "foreign_key": col,
                                    "confidence": "high",
                                }
                            )

        return relationships

    async def suggest_synthesis_strategy(
        self, analysis: Dict[str, Any], model_type: str = "gaussian_copula"
    ) -> Dict[str, Any]:
        """
        Suggest best synthesis strategy based on data analysis.

        Args:
            analysis: Dataset analysis results
            model_type: Preferred model type

        Returns:
            Synthesis strategy recommendations
        """
        strategy = {
            "model_type": model_type,
            "parameters": {},
            "preprocessing": [],
            "postprocessing": [],
        }

        # Determine if CTGAN would be better for complex distributions
        num_numeric = sum(1 for col in analysis["columns"] if col["data_type"] == "numeric")
        num_categorical = sum(1 for col in analysis["columns"] if col["data_type"] == "categorical")

        if num_categorical > num_numeric and num_categorical > 5:
            strategy["model_type"] = "ctgan"
            strategy["parameters"]["epochs"] = 300
        else:
            strategy["model_type"] = "gaussian_copula"

        # Suggest preprocessing for high cardinality columns
        for col in analysis["columns"]:
            if col["data_type"] == "string" and col["unique_count"] > 1000:
                strategy["preprocessing"].append(
                    {"column": col["name"], "action": "hash_or_anonymize"}
                )

        return strategy


# Global agent instance
_replication_agent: Optional[ReplicationAgent] = None


def get_replication_agent() -> ReplicationAgent:
    """Get or create the global replication agent instance"""
    global _replication_agent
    if _replication_agent is None:
        _replication_agent = ReplicationAgent()
    return _replication_agent
