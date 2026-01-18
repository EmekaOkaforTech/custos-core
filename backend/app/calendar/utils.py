import re


def normalize_identifier(identifier: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", identifier.strip().lower())
    return sanitized.strip("_")
