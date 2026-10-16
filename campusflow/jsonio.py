"""Low-level, dependency-free JSON reading and writing.

This module exists so that :mod:`campusflow.storage` and
:mod:`campusflow.categories` can share one *safe* writer without importing each
other. It imports nothing from the rest of the package except the error types,
so it can never take part in an import cycle.

Two safety properties matter here and are the reason this is not just two calls
to :mod:`json`:

* **Saves are atomic.** The data is written to a temporary file in the same
  directory and then moved into place with :func:`os.replace`. A crash midway
  through a save therefore leaves the previous good file intact instead of a
  half-written one. The original project wrote straight over the live file.
* **Duplicate keys can be detected.** ``json.load`` silently keeps the *last*
  of two identical keys, so ``{"T1": ..., "T1": ...}`` loads without complaint
  and one ticket vanishes. Passing ``reject_duplicate_keys=True`` uses an
  ``object_pairs_hook`` to refuse the file instead.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from campusflow.errors import DataError


def _reject_duplicate_keys(pairs):
    """``object_pairs_hook`` that refuses a JSON object with a repeated key."""
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise DataError(
                f"Duplicate key '{key}' in the JSON file. Refusing to load, "
                "because the duplicate would silently replace the earlier entry."
            )
        seen[key] = value
    return seen


def load_json(path, reject_duplicate_keys: bool = False):
    """Read one JSON file. Raises :class:`DataError` for unreadable content."""
    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as file:
            if reject_duplicate_keys:
                return json.load(file, object_pairs_hook=_reject_duplicate_keys)
            return json.load(file)
    except json.JSONDecodeError as error:
        raise DataError(f"{path} is not valid JSON: {error}") from error
    except OSError as error:
        raise DataError(f"{path} could not be read: {error}") from error


def save_json(path, data) -> None:
    """Write JSON atomically: temp file in the same directory, then replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def backup_file(path) -> Path | None:
    """Copy a file aside before it is replaced. Returns the backup path."""
    path = Path(path)
    if not path.exists():
        return None

    backup_path = path.with_suffix(path.suffix + ".bak")
    counter = 1
    while backup_path.exists():
        backup_path = path.with_suffix(path.suffix + f".bak.{counter}")
        counter += 1

    shutil.copy2(path, backup_path)
    return backup_path
