"""Structured JSON output extraction and lightweight schema validation."""
from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from .provider import LLMResponse

T = TypeVar("T")


class StructuredOutputError(ValueError):
    pass


def parse_json_output(response: LLMResponse | str, schema: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    text = response.content if isinstance(response, LLMResponse) else response
    if not text:
        raise StructuredOutputError("The model returned no text content")
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"Model output is not valid JSON: {exc}") from exc
    if schema:
        validate_schema(value, schema)
    return value


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$" ) -> None:
    expected = schema.get("type")
    type_map = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if expected in type_map and not isinstance(value, type_map[expected]):
        raise StructuredOutputError(f"{path} must be {expected}")
    if expected == "object":
        for name in schema.get("required", []):
            if name not in value:
                raise StructuredOutputError(f"{path}.{name} is required")
        for name, child in schema.get("properties", {}).items():
            if name in value:
                validate_schema(value[name], child, f"{path}.{name}")
    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{path}[{index}]")
