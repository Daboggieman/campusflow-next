"""Persistence: the tickets, counter, staff list and category files.

CampusFlow Next keeps the original layout — everything inside ``data_folder/``,
with ``tickets.json`` a JSON object keyed by ticket ID — but makes loading
strict and side-effect free.

The important changes:

* **No ``input()`` in this module.** The original ``load_tickets`` and
  ``validate_counter`` stopped halfway to ask the user whether to quit or start
  fresh, which made them impossible to test and meant a data-layer function
  could end the process. They now raise :class:`DataError`; the CLI decides
  what to offer.
* **Nothing is replaced until everything validates.** ``load_tickets`` builds a
  completely new dictionary and returns it only once every record has passed.
  A file that fails on its last ticket leaves the caller's existing tickets
  exactly as they were, rather than half-overwritten.
* **Saves are atomic** (see :mod:`campusflow.jsonio`).
* **The counter is reconciled on load**, so the next generated ID can never
  collide with an ID already in the file.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from campusflow.errors import DataError, ValidationError
from campusflow.jsonio import backup_file, load_json, save_json
from campusflow.tickets import ticket_number
from campusflow.validation import validate_ticket_collection

DATA_DIR = Path("data_folder")
TICKETS_FILE = DATA_DIR / "tickets.json"
COUNTER_FILE = DATA_DIR / "counter.json"
STAFF_FILE = DATA_DIR / "staff.json"
CATEGORIES_FILE = DATA_DIR / "categories.json"

#: The keys every stored ticket must carry. ``notes`` is required on the way
#: *out*; a file written before CampusFlow Next is still accepted without it,
#: because the dataclass supplies an empty list.
REQUIRED_TICKET_KEYS = (
    "id",
    "title",
    "category",
    "urgency",
    "affected_users",
    "priority",
    "status",
    "assigned_to",
)

DEFAULT_STAFF = [
    "Mr. Kingsley(HOC)",
    "Mr. Godswill",
    "Mr. Izzy",
    "Mr. Gabriel",
    "Mr. Emmanuel",
    "Mr. Ayuba",
]


@dataclass
class ApplicationData:
    """Everything the app needs at startup, plus anything it should warn about."""

    tickets: dict
    counter: int
    staff: list
    warnings: list = field(default_factory=list)


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not TICKETS_FILE.exists():
        save_tickets({})

    if not COUNTER_FILE.exists():
        save_counter(0)

    if not STAFF_FILE.exists():
        save_staff(DEFAULT_STAFF.copy())


def backup_broken_file(path) -> Path | None:
    """Copy an unusable file aside before the caller starts fresh."""
    backup_path = backup_file(path)
    if backup_path is not None:
        print(f"Backup created: {backup_path}")
    return backup_path


# --------------------------------------------------------------------------
# tickets
# --------------------------------------------------------------------------


def load_tickets(path=None) -> dict:
    """Load every ticket, or raise :class:`DataError` and change nothing."""
    path = Path(path) if path is not None else TICKETS_FILE

    if not path.exists():
        return {}

    data = load_json(path, reject_duplicate_keys=True)
    return validate_ticket_collection(data, source=str(path))


def save_tickets(tickets) -> None:
    """Write every ticket field, notes included."""
    data = {ticket_id: asdict(ticket) for ticket_id, ticket in tickets.items()}
    save_json(TICKETS_FILE, data)


# --------------------------------------------------------------------------
# counter
# --------------------------------------------------------------------------


def load_counter() -> int:
    if not COUNTER_FILE.exists():
        return 0

    data = load_json(COUNTER_FILE)
    if not isinstance(data, int) or isinstance(data, bool) or data < 0:
        raise DataError(
            f"The counter in {COUNTER_FILE} must be a non-negative integer."
        )
    return data


def save_counter(counter) -> None:
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        raise ValidationError("The counter must be a non-negative integer.")
    save_json(COUNTER_FILE, counter)


def highest_ticket_number(tickets) -> int:
    """The largest number used by any ticket ID, or 0 when there are none."""
    return max((ticket_number(ticket_id) for ticket_id in tickets), default=0)


def validate_counter(counter, tickets):
    """Reconcile the counter against the tickets actually on disk.

    Returns ``(counter, warnings)``. A counter lower than the highest existing
    ticket ID would hand out an ID that is already taken, so it is raised to
    match. Raising it is always safe: no ID is ever reused or skipped by doing
    so. This used to prompt the user; it is now a pure function.
    """
    highest = highest_ticket_number(tickets)

    if counter < highest:
        warning = (
            f"The ticket counter was {counter}, lower than the highest saved "
            f"ticket ID (T{highest}). It has been corrected to {highest} so "
            "the next ticket does not reuse an existing ID."
        )
        return highest, [warning]

    return counter, []


def generate_ticket_id(counter):
    """Issue the next ticket ID and persist the advanced counter."""
    new_counter = counter + 1
    ticket_id = f"T{new_counter}"
    save_counter(new_counter)
    return ticket_id, new_counter


# --------------------------------------------------------------------------
# staff
# --------------------------------------------------------------------------


def load_staff() -> list:
    if not STAFF_FILE.exists():
        save_staff(DEFAULT_STAFF.copy())
        return DEFAULT_STAFF.copy()

    staff = load_json(STAFF_FILE)

    if not isinstance(staff, list) or not all(
        isinstance(name, str) and name.strip() for name in staff
    ):
        raise DataError(f"The staff file {STAFF_FILE} must be a list of names.")

    return staff


def save_staff(staff) -> None:
    save_json(STAFF_FILE, staff)


# --------------------------------------------------------------------------
# startup
# --------------------------------------------------------------------------


def load_application_data() -> ApplicationData:
    """Load everything, validating the category list before the tickets.

    Order matters: tickets are validated against the *known* categories, so the
    registry has to be populated first or every ticket would look invalid.
    """
    from campusflow.categories import load_categories

    ensure_data_files()
    load_categories(CATEGORIES_FILE)

    tickets = load_tickets()
    counter = load_counter()
    staff = load_staff()

    counter, warnings = validate_counter(counter, tickets)
    if warnings:
        save_counter(counter)

    return ApplicationData(
        tickets=tickets, counter=counter, staff=staff, warnings=warnings
    )
