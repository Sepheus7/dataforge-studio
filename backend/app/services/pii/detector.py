"""PII detection using spacy NER"""

from typing import Dict, List, Set, Optional
import pandas as pd
import spacy
import re

from app.core.config import settings


class PIIDetector:
    """
    Detect PII (Personally Identifiable Information) in datasets using spacy.

    Detects common PII types including:
    - Names (PERSON)
    - Organizations (ORG)
    - Locations (GPE, LOC)
    - Emails
    - Phone numbers
    - SSN
    - Credit card numbers
    """

    def __init__(self):
        """Initialize PII detector"""
        self.nlp: Optional[spacy.Language] = None
        self._load_model()

        # Regex patterns for structured PII
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        }

    def _load_model(self):
        """Load spacy model"""
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL)
        except OSError:
            # Model not installed
            raise RuntimeError(
                f"Spacy model '{settings.SPACY_MODEL}' not found. "
                f"Install it with: python -m spacy download {settings.SPACY_MODEL}"
            )

    def detect_in_dataframe(self, df: pd.DataFrame, sample_size: int = 100) -> Dict[str, List[str]]:
        """
        Detect PII in a DataFrame.

        Args:
            df: Pandas DataFrame to analyze
            sample_size: Number of rows to sample for detection

        Returns:
            Dictionary mapping column names to list of detected PII types
        """
        results: Dict[str, Set[str]] = {}

        # Sample data for performance
        sample_df = df.head(sample_size) if len(df) > sample_size else df

        for column in df.columns:
            detected_types = set()

            # Skip non-string columns for NER
            if df[column].dtype not in ["object", "string"]:
                # Check for numeric patterns (SSN, credit card as numbers)
                if df[column].dtype in ["int64", "float64"]:
                    sample_values = sample_df[column].dropna().astype(str).tolist()
                    for value in sample_values[:20]:
                        if self.patterns["ssn"].match(value):
                            detected_types.add("ssn")
                        if self.patterns["credit_card"].match(value):
                            detected_types.add("credit_card")
                continue

            # Get sample values
            sample_values = sample_df[column].dropna().astype(str).tolist()

            # Check regex patterns
            for value in sample_values[:20]:  # Check first 20 values
                for pii_type, pattern in self.patterns.items():
                    if pattern.search(value):
                        detected_types.add(pii_type)

            # Check with NER for names, organizations, locations
            for value in sample_values[:50]:  # NER is slower
                if len(value) > 3 and len(value) < 200:  # Skip very short/long
                    doc = self.nlp(value)
                    for ent in doc.ents:
                        if ent.label_ == "PERSON":
                            detected_types.add("person_name")
                        elif ent.label_ == "ORG":
                            detected_types.add("organization")
                        elif ent.label_ in ["GPE", "LOC"]:
                            detected_types.add("location")

            # Heuristic checks based on column name
            col_lower = column.lower()
            if any(keyword in col_lower for keyword in ["email", "mail"]):
                detected_types.add("email")
            if any(keyword in col_lower for keyword in ["phone", "tel", "mobile"]):
                detected_types.add("phone")
            if any(keyword in col_lower for keyword in ["ssn", "social_security"]):
                detected_types.add("ssn")
            if any(keyword in col_lower for keyword in ["name", "first", "last"]):
                detected_types.add("person_name")
            if any(keyword in col_lower for keyword in ["address", "street", "city", "zip"]):
                detected_types.add("location")

            if detected_types:
                results[column] = list(detected_types)

        return results

    def detect_in_text(self, text: str) -> List[Dict[str, str]]:
        """
        Detect PII entities in a text string.

        Args:
            text: Text to analyze

        Returns:
            List of detected entities with type and value
        """
        entities = []

        # Regex patterns
        for pii_type, pattern in self.patterns.items():
            matches = pattern.finditer(text)
            for match in matches:
                entities.append(
                    {
                        "type": pii_type,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        # NER
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]:
                entities.append(
                    {
                        "type": ent.label_.lower(),
                        "value": ent.text,
                        "start": ent.start_char,
                        "end": ent.end_char,
                    }
                )

        return entities

    def is_pii_column(self, column_name: str, sample_values: List[str]) -> bool:
        """
        Quick check if a column likely contains PII.

        Args:
            column_name: Name of the column
            sample_values: Sample values from the column

        Returns:
            True if PII is likely present
        """
        col_lower = column_name.lower()

        # Check column name
        pii_keywords = [
            "name",
            "email",
            "phone",
            "ssn",
            "social",
            "address",
            "street",
            "city",
            "zip",
            "credit",
            "card",
            "passport",
        ]
        if any(keyword in col_lower for keyword in pii_keywords):
            return True

        # Check sample values
        for value in sample_values[:10]:
            if isinstance(value, str):
                for pattern in self.patterns.values():
                    if pattern.search(value):
                        return True

        return False


# Global detector instance
_detector: Optional[PIIDetector] = None


def get_pii_detector() -> PIIDetector:
    """Get or create the global PII detector instance"""
    global _detector
    if _detector is None:
        _detector = PIIDetector()
    return _detector
