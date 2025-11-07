"""PII replacement strategies"""

from typing import Dict, List, Optional
import pandas as pd
import hashlib
from faker import Faker
import random


class PIIReplacer:
    """
    Replace PII in datasets with synthetic data.

    Supports multiple replacement strategies:
    - fake: Replace with realistic fake data using Faker
    - hash: Replace with cryptographic hash
    - redact: Replace with [REDACTED]
    - tokenize: Replace with tokens (ID_001, ID_002, etc.)
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize PII replacer.

        Args:
            seed: Random seed for reproducible replacement
        """
        self.faker = Faker()
        if seed is not None:
            random.seed(seed)
            self.faker.seed_instance(seed)

        self._token_counters: Dict[str, int] = {}
        self._hash_cache: Dict[str, str] = {}

    def replace_in_dataframe(
        self, df: pd.DataFrame, pii_map: Dict[str, List[str]], strategy: str = "fake"
    ) -> pd.DataFrame:
        """
        Replace PII in a DataFrame.

        Args:
            df: Pandas DataFrame
            pii_map: Dictionary mapping column names to PII types
            strategy: Replacement strategy (fake, hash, redact, tokenize)

        Returns:
            DataFrame with PII replaced
        """
        df_copy = df.copy()

        for column, pii_types in pii_map.items():
            if column not in df_copy.columns:
                continue

            # Choose replacement function based on PII type
            primary_type = pii_types[0] if pii_types else "unknown"

            if strategy == "fake":
                df_copy[column] = df_copy[column].apply(
                    lambda x: self._fake_replacement(x, primary_type)
                )
            elif strategy == "hash":
                df_copy[column] = df_copy[column].apply(lambda x: self._hash_replacement(x))
            elif strategy == "redact":
                df_copy[column] = "[REDACTED]"
            elif strategy == "tokenize":
                df_copy[column] = df_copy[column].apply(
                    lambda x: self._token_replacement(x, column)
                )
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

        return df_copy

    def _fake_replacement(self, value: any, pii_type: str) -> any:
        """Replace with fake data based on PII type"""
        if pd.isna(value):
            return value

        if pii_type == "email":
            return self.faker.email()
        elif pii_type == "phone":
            return self.faker.phone_number()
        elif pii_type == "person_name":
            return self.faker.name()
        elif pii_type == "ssn":
            return self.faker.ssn()
        elif pii_type == "credit_card":
            return self.faker.credit_card_number()
        elif pii_type == "location":
            return self.faker.city()
        elif pii_type == "organization":
            return self.faker.company()
        else:
            # Generic replacement
            return self.faker.word()

    def _hash_replacement(self, value: any) -> str:
        """Replace with SHA256 hash"""
        if pd.isna(value):
            return value

        value_str = str(value)

        # Use cache for consistency
        if value_str in self._hash_cache:
            return self._hash_cache[value_str]

        hashed = hashlib.sha256(value_str.encode()).hexdigest()[:16]
        self._hash_cache[value_str] = hashed

        return hashed

    def _token_replacement(self, value: any, column: str) -> str:
        """Replace with sequential token"""
        if pd.isna(value):
            return value

        if column not in self._token_counters:
            self._token_counters[column] = 0

        self._token_counters[column] += 1
        return f"{column.upper()[:3]}_{self._token_counters[column]:05d}"

    def replace_column(self, series: pd.Series, pii_type: str, strategy: str = "fake") -> pd.Series:
        """
        Replace PII in a single column.

        Args:
            series: Pandas Series
            pii_type: Type of PII
            strategy: Replacement strategy

        Returns:
            Series with PII replaced
        """
        if strategy == "fake":
            return series.apply(lambda x: self._fake_replacement(x, pii_type))
        elif strategy == "hash":
            return series.apply(self._hash_replacement)
        elif strategy == "redact":
            return pd.Series(["[REDACTED]"] * len(series), index=series.index)
        elif strategy == "tokenize":
            return series.apply(lambda x: self._token_replacement(x, series.name))
        else:
            raise ValueError(f"Unknown strategy: {strategy}")


# Global replacer instance
_replacer: Optional[PIIReplacer] = None


def get_pii_replacer(seed: Optional[int] = None) -> PIIReplacer:
    """Get or create a PII replacer instance"""
    global _replacer
    if _replacer is None or seed is not None:
        _replacer = PIIReplacer(seed=seed)
    return _replacer
