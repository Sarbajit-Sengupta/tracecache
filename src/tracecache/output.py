"""Local output safety: file-identity checks and atomic single-file replacement."""

import os
import tempfile
from collections.abc import Sequence
from pathlib import Path


def check_distinct(paths: Sequence[Path]) -> None:
    for index, path in enumerate(paths):
        for previous in paths[:index]:
            if path.resolve() == previous.resolve() or (
                path.exists() and previous.exists() and path.samefile(previous)
            ):
                raise ValueError("input and output paths must refer to distinct files")


def atomic_write(path: Path, content: str) -> None:
    """Replace one file only after its complete contents have been flushed.

    Multiple calls do not constitute a multi-file transaction. Directory fsync
    and a guarantee against power loss are deliberately outside this contract.
    """
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=".tracecache-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
