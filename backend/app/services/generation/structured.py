"""Structured data generation service - migrated and enhanced from original DataForge"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import random
from faker import Faker
from datetime import datetime, timedelta
import asyncio

from app.core.config import settings
from app.services.jobs import get_job_manager
import logging
logger = logging.getLogger(__name__)


class StructuredDataGenerator:
    """
    Service for generating structured synthetic datasets.

    Supports multi-table generation with referential integrity,
    various column types, and deterministic seeding.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the generator.

        Args:
            base_dir: Base directory for artifacts (None uses config)
        """
        if base_dir is None:
            base_dir = Path(settings.LOCAL_ARTIFACTS_DIR)
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.job_manager = get_job_manager()

    def _job_dir(self, job_id: str) -> Path:
        """Get or create job directory"""
        d = self.base_dir / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def generate_from_schema(self, job_id: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate data from a schema definition.

        Args:
            job_id: Job identifier
            schema: Schema dictionary

        Returns:
            Summary of generated data
        """
        logger.info(f"🔧 generate_from_schema called for job {job_id}")
        job_dir = self._job_dir(job_id)
        logger.info(f"📁 Job directory: {job_dir}")
        faker = Faker()

        # Set up seed
        seed = schema.get("seed")
        if seed is not None:
            random.seed(seed)
            faker.seed_instance(seed)

        # Save schema
        schema_path = job_dir / "schema.json"
        schema_path.write_text(json.dumps(schema, indent=2))
        logger.info(f"💾 Schema saved to {schema_path}")

        tables = schema.get("tables", [])
        logger.info(f"📊 Found {len(tables)} tables to generate")
        summary_tables = []
        pk_values: Dict[str, List[str]] = {}

        total_tables = len(tables)

        for table_idx, table in enumerate(tables):
            logger.info(f"🔨 Generating table {table_idx + 1}/{total_tables}: {table.get('name', 'unknown')}")
            # Update progress (map data generation to 95-100% range)
            # Schema inference uses 0-95%, data generation uses 95-100%
            table_progress = table_idx / total_tables if total_tables > 0 else 0
            progress = 0.95 + (0.05 * table_progress)
            self.job_manager.update_progress(
                job_id,
                progress,
                f"📊 Generating table {table_idx + 1}/{total_tables}: {table['name']}",
            )

            table_summary = await self._generate_table(
                table=table, 
                job_dir=job_dir, 
                faker=faker, 
                pk_values=pk_values,
                job_id=job_id,
                table_idx=table_idx,
                total_tables=total_tables
            )

            summary_tables.append(table_summary)

            # Yield control to allow other async operations
            await asyncio.sleep(0)

        summary = {
            "tables": summary_tables,
            "total_rows": sum(t["rows"] for t in summary_tables),
            "total_columns": sum(t["columns"] for t in summary_tables),
        }

        return summary

    async def _generate_table(
        self, 
        table: Dict[str, Any], 
        job_dir: Path, 
        faker: Faker, 
        pk_values: Dict[str, List[str]],
        job_id: str,
        table_idx: int,
        total_tables: int
    ) -> Dict[str, Any]:
        """
        Generate a single table.

        Args:
            table: Table schema
            job_dir: Job directory
            faker: Faker instance
            pk_values: Dictionary of primary key values for FK references

        Returns:
            Table summary
        """
        name = table["name"]
        rows_raw = table.get("rows", 1000)

        # Parse rows
        try:
            rows = int(rows_raw) if rows_raw is not None else 1000
        except (TypeError, ValueError):
            rows = 1000

        rows = max(1, min(rows, settings.MAX_ROWS_PER_TABLE))

        # Prepare columns
        raw_columns = table.get("columns", [])
        columns = [str(c.get("name")) for c in raw_columns if isinstance(c, dict) and c.get("name")]

        # Handle primary key
        pk_decl = table.get("primary_key")
        pk_field: Optional[str] = None
        if isinstance(pk_decl, list) and pk_decl:
            pk_field = str(pk_decl[0])
        elif isinstance(pk_decl, str):
            pk_field = pk_decl

        if pk_field and pk_field not in columns:
            columns = [pk_field, *columns]

        # Prepare foreign keys
        fk_cfg = table.get("foreign_keys", [])
        fk_pools: Dict[str, List[str]] = {}
        for fk in fk_cfg:
            ref_table = fk.get("ref_table")
            ref_col = fk.get("ref_column")
            if ref_table and ref_col and ref_table in pk_values:
                fk_pools[fk["column"]] = pk_values[ref_table]

        # Write CSV header
        csv_path = job_dir / f"{name}.csv"
        with open(csv_path, "w", newline="") as f:
            f.write(",".join(columns) + "\n")

        generated_pk_values: List[str] = []

        # Detect special generation modes
        normalized_cols = [c.lower() for c in columns]
        is_timeseries = self._is_timeseries(normalized_cols)

        # Precompute timeseries parameters
        if is_timeseries:
            start_date = datetime.utcnow().date() - timedelta(days=rows)
            base_price = max(10.0, random.random() * 100)
            drift = random.uniform(-0.001, 0.001)
        else:
            start_date = None
            base_price = None
            drift = None

        # Generate rows with progress updates
        chunk_size = max(10000, rows // 20)  # Update every 10k rows or 5% progress, whichever is larger
        last_progress_update = 0
        
        for i in range(rows):
            values = []
            derived_row: Dict[str, Any] = {}

            # Compute derived values for timeseries
            if is_timeseries:
                derived_row = self._generate_timeseries_row(i, start_date, base_price, drift)
                base_price = derived_row.get("close", base_price)

            # Generate column values
            for col in columns:
                if pk_field and col == pk_field:
                    pk = self._fake_value({"type": "uuid"}, faker, i)
                    generated_pk_values.append(str(pk))
                    values.append(str(pk))
                elif col in fk_pools:
                    ref_val = random.choice(fk_pools[col])
                    values.append(str(ref_val))
                else:
                    col_cfg = next(
                        (c for c in raw_columns if isinstance(c, dict) and c.get("name") == col),
                        {"type": "string"},
                    )

                    # Use derived value if available
                    if col in derived_row:
                        values.append(str(derived_row[col]))
                    elif col.lower() in derived_row:
                        values.append(str(derived_row[col.lower()]))
                    else:
                        values.append(str(self._fake_value(col_cfg, faker, i)))

            # Write row
            with open(csv_path, "a", newline="") as f:
                f.write(",".join(values) + "\n")

            # Update progress periodically during generation
            if i > 0 and (i - last_progress_update) >= chunk_size:
                # Calculate progress within this table (0-1)
                table_internal_progress = i / rows
                # Map to overall progress (95-100% range)
                # Each table gets 5% / total_tables of the 95-100% range
                table_base_progress = table_idx / total_tables if total_tables > 0 else 0
                table_range_progress = (table_idx + table_internal_progress) / total_tables if total_tables > 0 else 0
                overall_progress = 0.95 + (0.05 * table_range_progress)
                
                # Update progress
                self.job_manager.update_progress(
                    job_id,
                    overall_progress,
                    f"📊 Generating table {table_idx + 1}/{total_tables}: {table['name']} ({i:,}/{rows:,} rows)",
                )
                await asyncio.sleep(0)
                last_progress_update = i

        # Store PK values for FK references
        if generated_pk_values:
            pk_values[name] = generated_pk_values

        # Create JSON preview
        json_path = job_dir / f"{name}.json"
        preview = {"table": name, "rows": rows, "columns": columns, "sample_size": min(100, rows)}
        json_path.write_text(json.dumps(preview, indent=2))

        return {
            "name": name,
            "rows": rows,
            "columns": len(columns),
            "size_bytes": csv_path.stat().st_size,
        }

    def _is_timeseries(self, column_names: List[str]) -> bool:
        """Check if columns indicate timeseries data"""
        has_date = any(c in column_names for c in ["date", "datetime", "ts"])
        has_ohlc = (
            any(c in column_names for c in ["open", "opening_price"])
            and any(c in column_names for c in ["close", "closing_price"])
            and any(c in column_names for c in ["high", "highest_price"])
            and any(c in column_names for c in ["low", "lowest_price"])
        )
        return has_date and has_ohlc

    def _generate_timeseries_row(
        self, index: int, start_date: datetime, base_price: float, drift: float
    ) -> Dict[str, Any]:
        """Generate OHLC timeseries data"""
        current_date = start_date + timedelta(days=index)

        # Random walk
        step = random.gauss(drift, 0.02)
        open_price = max(0.01, base_price * (1.0 + step))
        close_price = max(0.01, open_price * (1.0 + random.gauss(0, 0.01)))
        high_price = max(open_price, close_price) * (1.0 + abs(random.gauss(0, 0.01)))
        low_price = min(open_price, close_price) * (1.0 - abs(random.gauss(0, 0.01)))
        volume_val = int(max(1, random.lognormvariate(5.0, 0.5)))
        price_change_pct = ((close_price - open_price) / open_price) * 100.0

        return {
            "date": str(current_date),
            "datetime": f"{current_date}T00:00:00",
            "ts": f"{current_date}T00:00:00",
            "open": round(open_price, 2),
            "opening_price": round(open_price, 2),
            "close": round(close_price, 2),
            "closing_price": round(close_price, 2),
            "high": round(high_price, 2),
            "highest_price": round(high_price, 2),
            "low": round(low_price, 2),
            "lowest_price": round(low_price, 2),
            "price_change_percentage": round(price_change_pct, 4),
            "current_price": round(close_price, 2),
            "volume": volume_val,
        }

    def _fake_value(self, col_cfg: Dict[str, Any], faker: Faker, index: int) -> Any:
        """Generate a fake value based on column configuration"""
        col_type = (col_cfg.get("type") or "string").lower()

        # Handle specific types
        if col_type in {"uuid"}:
            return faker.uuid4()
        if col_type in {"int", "integer"}:
            range_cfg = col_cfg.get("range", {})
            min_val = range_cfg.get("min", 0)
            max_val = range_cfg.get("max", 1000)
            return random.randint(min_val, max_val)
        if col_type in {"float", "double"}:
            return round(random.random() * 1000, 2)
        if col_type in {"string", "text"}:
            return faker.word()
        if col_type in {"email"}:
            return faker.email()
        if col_type in {"first_name"}:
            return faker.first_name()
        if col_type in {"last_name"}:
            return faker.last_name()
        if col_type in {"date"}:
            return str(faker.date_between(start_date="-3y", end_date="today"))
        if col_type in {"datetime", "timestamp"}:
            return faker.date_time_between(start_date="-3y", end_date="now").isoformat()
        if col_type in {"boolean", "bool"}:
            prob = col_cfg.get("probability", 0.5)
            return random.random() < float(prob)
        if col_type in {"categorical"}:
            cats = col_cfg.get("categories", ["A", "B", "C"])
            weights = col_cfg.get("weights")
            if weights and len(weights) == len(cats):
                return random.choices(cats, weights=weights)[0]
            return random.choice(cats)

        # Fallback
        return faker.pystr(min_chars=5, max_chars=12)

    def get_artifact_path(
        self, job_id: str, table_name: str, format: str = "csv"
    ) -> Optional[Path]:
        """
        Get path to generated artifact.

        Args:
            job_id: Job identifier
            table_name: Table name
            format: File format (csv, json)

        Returns:
            Path to artifact or None if not found
        """
        job_dir = self._job_dir(job_id)
        artifact_path = job_dir / f"{table_name}.{format}"

        if artifact_path.exists():
            return artifact_path

        return None


# Global instance
_generator: Optional[StructuredDataGenerator] = None


def get_structured_generator() -> StructuredDataGenerator:
    """Get or create the global generator instance"""
    global _generator
    if _generator is None:
        _generator = StructuredDataGenerator()
    return _generator
