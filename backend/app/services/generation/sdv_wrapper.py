"""SDV (Synthetic Data Vault) wrapper for dataset replication"""

from typing import Dict, Any, Optional, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Try to import SDV, make it optional due to binary compatibility issues
try:
    from sdv.single_table import GaussianCopulaSynthesizer, CTGANSynthesizer
    from sdv.metadata import SingleTableMetadata
    from sdv.multi_table import HMASynthesizer
    from sdv.metadata import MultiTableMetadata
    from sdv.evaluation.single_table import evaluate_quality
    SDV_AVAILABLE = True
except (ImportError, SystemError, OSError) as e:
    SDV_AVAILABLE = False
    SDV_ERROR = str(e)
    logger.warning(f"SDV not available: {SDV_ERROR}. Dataset replication features will be disabled.")
    # Create dummy classes to prevent import errors
    GaussianCopulaSynthesizer = None
    CTGANSynthesizer = None
    SingleTableMetadata = None
    HMASynthesizer = None
    MultiTableMetadata = None
    evaluate_quality = None


class SDVReplicator:
    """
    Wrapper for SDV library to replicate datasets with statistical fidelity.

    Supports both single-table and multi-table synthesis with various models.
    """

    def __init__(self):
        """Initialize SDV replicator"""
        self.models: Dict[str, Any] = {}
        self.metadata_cache: Dict[str, Any] = {}

    def analyze_dataset(self, df: pd.DataFrame, table_name: str = "data") -> Dict[str, Any]:
        """
        Analyze a dataset to understand its structure.

        Args:
            df: Pandas DataFrame
            table_name: Name of the table

        Returns:
            Analysis results
        """
        analysis = {
            "table_name": table_name,
            "num_rows": len(df),
            "num_columns": len(df.columns),
            "columns": [],
            "dtypes": {},
            "missing_percentages": {},
            "unique_counts": {},
        }

        for col in df.columns:
            col_info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "unique_count": df[col].nunique(),
                "null_percentage": (df[col].isnull().sum() / len(df)) * 100,
            }

            # Determine SDV dtype
            if df[col].dtype in ["int64", "int32"]:
                col_info["sdv_type"] = "numerical"
                col_info["min"] = int(df[col].min()) if not df[col].isnull().all() else None
                col_info["max"] = int(df[col].max()) if not df[col].isnull().all() else None
            elif df[col].dtype in ["float64", "float32"]:
                col_info["sdv_type"] = "numerical"
                col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
            elif df[col].dtype == "object" or str(df[col].dtype) == "string":
                if df[col].nunique() < 50:  # Threshold for categorical
                    col_info["sdv_type"] = "categorical"
                else:
                    col_info["sdv_type"] = "text"
            elif df[col].dtype == "bool":
                col_info["sdv_type"] = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                col_info["sdv_type"] = "datetime"
            else:
                col_info["sdv_type"] = "unknown"

            analysis["columns"].append(col_info)
            analysis["dtypes"][col] = str(df[col].dtype)
            analysis["missing_percentages"][col] = col_info["null_percentage"]
            analysis["unique_counts"][col] = col_info["unique_count"]

        return analysis

    def detect_relationships(self, tables: Dict[str, pd.DataFrame]) -> List[Dict[str, str]]:
        """
        Detect potential foreign key relationships between tables.

        Args:
            tables: Dictionary of table_name -> DataFrame

        Returns:
            List of detected relationships
        """
        relationships = []
        table_names = list(tables.keys())

        for i, parent_table in enumerate(table_names):
            parent_df = tables[parent_table]

            for child_table in table_names[i + 1 :]:
                child_df = tables[child_table]

                # Find common columns
                common_cols = set(parent_df.columns) & set(child_df.columns)

                for col in common_cols:
                    # Check if column might be a foreign key
                    if col.endswith("_id") or col == "id":
                        parent_vals = set(parent_df[col].dropna().unique())
                        child_vals = set(child_df[col].dropna().unique())

                        # Child values should be subset of parent values
                        if child_vals.issubset(parent_vals) and len(child_vals) > 0:
                            relationships.append(
                                {
                                    "parent_table": parent_table,
                                    "child_table": child_table,
                                    "parent_column": col,
                                    "child_column": col,
                                }
                            )

        return relationships

    def train_model(
        self,
        df: pd.DataFrame,
        model_type: str = "gaussian_copula",
        table_name: str = "data",
        primary_key: Optional[str] = None,
    ) -> str:
        """
        Train a synthesizer model on the dataset.

        Args:
            df: Training data
            model_type: Type of model (gaussian_copula, ctgan)
            table_name: Name of the table
            primary_key: Primary key column (if any)

        Returns:
            Model ID
        """
        if not SDV_AVAILABLE:
            raise NotImplementedError(f"SDV not available: {SDV_ERROR}. Please use prompt-based generation instead.")
        
        # Create metadata
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(df)

        if primary_key and primary_key in df.columns:
            metadata.set_primary_key(primary_key)

        # Create and train model
        if model_type.lower() == "ctgan":
            model = CTGANSynthesizer(metadata=metadata, epochs=300, verbose=False)
        else:  # gaussian_copula
            model = GaussianCopulaSynthesizer(metadata=metadata, default_distribution="norm")

        logger.info(f"Training {model_type} model on {len(df)} rows...")
        model.fit(df)

        # Store model
        model_id = f"{table_name}_{model_type}"
        self.models[model_id] = model
        self.metadata_cache[model_id] = metadata

        logger.info(f"Model {model_id} trained successfully")
        return model_id

    def generate_synthetic(self, model_id: str, num_rows: int) -> pd.DataFrame:
        """
        Generate synthetic data using a trained model.

        Args:
            model_id: Trained model identifier
            num_rows: Number of rows to generate

        Returns:
            Synthetic DataFrame
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found. Train a model first.")

        model = self.models[model_id]

        logger.info(f"Generating {num_rows} synthetic rows...")
        synthetic_df = model.sample(num_rows=num_rows)

        return synthetic_df

    def evaluate_quality(
        self, real_data: pd.DataFrame, synthetic_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of synthetic data compared to real data.

        Args:
            real_data: Original dataset
            synthetic_data: Synthetic dataset

        Returns:
            Quality metrics
        """
        if not SDV_AVAILABLE:
            raise NotImplementedError(f"SDV not available: {SDV_ERROR}. Please use prompt-based generation instead.")
        
        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(real_data)

        quality_report = evaluate_quality(
            real_data=real_data, synthetic_data=synthetic_data, metadata=metadata
        )

        return {
            "overall_quality": quality_report.get_score(),
            "column_shapes": quality_report.get_details("Column Shapes"),
            "column_pair_trends": quality_report.get_details("Column Pair Trends"),
        }

    def train_multi_table_model(
        self, tables: Dict[str, pd.DataFrame], relationships: List[Dict[str, str]]
    ) -> str:
        """
        Train a multi-table synthesizer.

        Args:
            tables: Dictionary of table_name -> DataFrame
            relationships: List of relationship definitions

        Returns:
            Model ID
        """
        if not SDV_AVAILABLE:
            raise NotImplementedError(f"SDV not available: {SDV_ERROR}. Please use prompt-based generation instead.")
        
        # Create metadata
        metadata = MultiTableMetadata()

        for table_name, df in tables.items():
            metadata.detect_table_from_dataframe(table_name, df)

        # Add relationships
        for rel in relationships:
            metadata.add_relationship(
                parent_table_name=rel["parent_table"],
                child_table_name=rel["child_table"],
                parent_primary_key=rel["parent_column"],
                child_foreign_key=rel["child_column"],
            )

        # Create and train model
        model = HMASynthesizer(metadata)

        logger.info(f"Training multi-table model on {len(tables)} tables...")
        model.fit(tables)

        # Store model
        model_id = f"multi_table_{'_'.join(tables.keys())}"
        self.models[model_id] = model
        self.metadata_cache[model_id] = metadata

        logger.info(f"Multi-table model {model_id} trained successfully")
        return model_id

    def generate_multi_table_synthetic(
        self, model_id: str, scale: float = 1.0
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate synthetic multi-table data.

        Args:
            model_id: Trained model identifier
            scale: Scaling factor for number of rows

        Returns:
            Dictionary of synthetic DataFrames
        """
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]

        logger.info(f"Generating multi-table synthetic data with scale={scale}...")
        synthetic_tables = model.sample(scale=scale)

        return synthetic_tables


# Global instance
_replicator: Optional[SDVReplicator] = None


def get_sdv_replicator() -> SDVReplicator:
    """Get or create the global SDV replicator instance"""
    global _replicator
    if _replicator is None:
        _replicator = SDVReplicator()
    return _replicator
