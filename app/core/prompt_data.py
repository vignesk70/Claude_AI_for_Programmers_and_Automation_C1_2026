import json
from typing import Any


def serialize_prompt_payload(payload: dict[str, Any]) -> str:
    """Turn application data into a clean JSON string for LLM prompts.

    Args:
        payload: The prompt data to serialize.

    Returns:
        A JSON string representing the serialized prompt data.
    """
    return json.dumps(payload, ensure_ascii=False, indent=2)
