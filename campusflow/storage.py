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
    backup_path = backup_file(path)
    if backup_path is not None:
        print(f"Backup created: {backup_path}")
    return backup_path

def load_tickets(path=None) -> dict:
    path = Path(path) if path is not None else TICKETS_FILE

    if not path.exists():
        return {}

    data = load_json(path, reject_duplicate_keys=True)
    return validate_ticket_collection(data, source=str(path))


def save_tickets(tickets) -> None:
    data = {ticket_id: asdict(ticket) for ticket_id, ticket in tickets.items()}
    save_json(TICKETS_FILE, data)

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
    return max((ticket_number(ticket_id) for ticket_id in tickets), default=0)


def validate_counter(counter, tickets):
    highest = highest_ticket_number(tickets)

    if counter < highest:
        warning = (
            f"The ticket counter was {counter}, lower than the highest saved "
            f"ticket ID (T{highest}). It has been corrected to {highest} so "
            "the next ticket does not reuse an existing ID."
        )
        return highest, [warning]

    return counter, []


def next_ticket_id(counter):
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        raise ValidationError("The counter must be a non-negative integer.")

    new_counter = counter + 1
    return f"T{new_counter}", new_counter


def generate_ticket_id(counter):
    ticket_id, new_counter = next_ticket_id(counter)
    save_counter(new_counter)
    return ticket_id, new_counter

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

def load_application_data() -> ApplicationData:
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
