from pathlib import Path
from typing import Optional


def safe_static_file(base: Path, relative: str) -> Optional[Path]:
    """Resolve a file under base; return None if path escapes base or is invalid."""
    if not relative or relative.startswith("/"):
        return None
    if ".." in relative.split("/"):
        return None
    try:
        resolved = (base / relative).resolve()
        base_resolved = base.resolve()
        resolved.relative_to(base_resolved)
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() else None
