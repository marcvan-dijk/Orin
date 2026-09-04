"""Structured interchange frontend for loading semantic models."""

import json
from pathlib import Path
from typing import Any

from orin_model import SemanticModel


class StructuredOrinFrontend:
    """Load a structured interchange document as a semantic model."""

    def parse_file(self, path: str | Path) -> SemanticModel:
        with Path(path).open(encoding="utf-8") as file:
            document = json.load(file)
        if not isinstance(document, dict):
            raise ValueError("structured frontend input must be a JSON object")
        return SemanticModel(document)

    def parse(self, text: str) -> SemanticModel:
        document: Any = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError("structured frontend input must be a JSON object")
        return SemanticModel(document)
