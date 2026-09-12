import re
from datetime import timedelta

DURATION_PATTERN = re.compile(r"(\d+)([dhms])")
UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration(text: str) -> timedelta | None:
    """Parses strings like '2h', '1d30m', '90s' (combinable). Returns None if unparseable."""
    matches = DURATION_PATTERN.findall(text.strip().lower())
    if not matches:
        return None
    total_seconds = sum(int(value) * UNIT_SECONDS[unit] for value, unit in matches)
    if total_seconds <= 0:
        return None
    return timedelta(seconds=total_seconds)