from pathlib import Path
from campusflow.errors import DataError, ValidationError
from campusflow.jsonio import load_json, save_json

DEFAULT_CATEGORIES = [
    "network",
    "hardware",
    "software",
    "administrative",
    "other",
]

_active: list[str] = list(DEFAULT_CATEGORIES)
_retired: list[str] = []

def get_categories() -> list[str]:
    """categories a new ticket may use, in display order."""
    return list(_active)

def get_retired_categories() -> list[str]:
    """categories that are no longer offered but are still accepted on load."""
    return list(_retired)

def get_known_categories() -> list[str]:
    """active + retired: everything a saved ticket may carry."""
    return list(_active) + list(_retired)


def reset_categories() -> None:
    """restore the shipped defaults."""
    global _active, _retired
    _active = list(DEFAULT_CATEGORIES)
    _retired = []


def check_category_name(raw_name) -> str:
    """Normalise one category name to its stored spelling.

    Names are stored casefolded and trimmed, matching the lowercase spellings
    the original project used for ``network``/``hardware``/``software``.
    """
    if not isinstance(raw_name, str):
        raise ValidationError("A category name must be text.")
    name = raw_name.strip().casefold()
    if not name:
        raise ValidationError("A category name cannot be blank.")
    return name


def set_categories(active, retired=None) -> None:
    """Replace the registry. Used when loading from disk and by tests."""
    global _active, _retired

    cleaned_active: list[str] = []
    seen: set[str] = set()
    for raw_name in active:
        name = check_category_name(raw_name)
        if name in seen:
            raise ValidationError(f"Duplicate category name: '{name}'.")
        seen.add(name)
        cleaned_active.append(name)

    if not cleaned_active:
        raise ValidationError("There must be at least one active category.")

    cleaned_retired: list[str] = []
    for raw_name in retired or []:
        name = check_category_name(raw_name)
        # A name cannot be both active and retired; active wins.
        if name in seen or name in cleaned_retired:
            continue
        cleaned_retired.append(name)

    _active = cleaned_active
    _retired = cleaned_retired


def add_category(raw_name) -> str:
    """Return an existing category to the active list, or create a new one."""
    name = check_category_name(raw_name)
    if name in _active:
        raise ValidationError(f"'{name}' is already an active category.")

    if name in _retired:
        # Reviving keeps the original spelling, so old tickets still match.
        _retired.remove(name)
        _active.append(name)
        return name

    _active.append(name)
    return name


def retire_category(raw_name) -> str:
    """Stop offering a category without losing tickets that already use it."""
    name = check_category_name(raw_name)
    if name not in _active:
        raise ValidationError(f"'{name}' is not an active category.")
    if len(_active) == 1:
        raise ValidationError("The last active category cannot be retired.")

    _active.remove(name)
    if name not in _retired:
        _retired.append(name)
    return name


def categories_to_dict() -> dict:
    """The on-disk envelope."""
    return {"active": list(_active), "retired": list(_retired)}


def load_categories(path) -> None:
    """Load the category registry, seeding the file on a first run.

    A plain JSON list is also accepted as the active set, so a hand-written
    file does not have to know about the envelope.
    """
    path = Path(path)

    if not path.exists():
        save_categories(path)
        return

    data = load_json(path)

    if isinstance(data, list):
        data = {"active": data, "retired": []}

    if not isinstance(data, dict):
        raise DataError(
            f"{path} must contain a JSON object with an 'active' list."
        )
    if "active" not in data:
        raise DataError(f"{path} is missing the 'active' list.")

    try:
        set_categories(data["active"], data.get("retired"))
    except ValidationError as error:
        raise DataError(f"{path} is invalid: {error}") from error


def save_categories(path) -> None:
    """Write the registry."""
    save_json(Path(path), categories_to_dict())
