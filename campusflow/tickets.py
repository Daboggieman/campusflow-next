import re
from dataclasses import dataclass, field

from campusflow.categories import get_known_categories
from campusflow.errors import ValidationError
URGENCIES = ("low", "medium", "high")
STATUSES = ("open", "in_progress", "resolved")
PRIORITIES = ("critical", "high", "medium", "low")

NOTE_ALLOWED_STATUSES = ("open", "in_progress")
NOTE_MESSAGE_MIN_LENGTH = 5
NOTE_MESSAGE_MAX_LENGTH = 450
TICKET_ID_PATTERN = re.compile(r"^T(\d+)$")
NOTE_ID_PATTERN = re.compile(r"^N(\d{3,})$")
NOTE_KEYS = ("note_id", "author", "message")

def _check_choice(raw_value, allowed, label):
    if not isinstance(raw_value, str):
        raise ValidationError(f"{label} must be text.")
    wanted = raw_value.strip().casefold()
    for option in allowed:
        if option.casefold() == wanted:
            return option
    raise ValidationError(
        f"'{raw_value}' is not a valid {label.lower()}. "
        f"Choose one of: {', '.join(allowed)}."
    )

def check_title(raw_title) -> str:
    if not isinstance(raw_title, str):
        raise ValidationError("Title must be text.")
    title = raw_title.strip().lower()
    if not title:
        raise ValidationError("Title cannot be blank.")
    return title

def check_ticket_id(raw_id) -> str:
    if not isinstance(raw_id, str):
        raise ValidationError("A ticket ID must be text.")
    cleaned = raw_id.strip().upper()
    match = TICKET_ID_PATTERN.match(cleaned)
    if not match or int(match.group(1)) < 1:
        raise ValidationError(
            f"'{raw_id}' is not a valid ticket ID (expected T1, T2, ...)."
        )
    return cleaned

def ticket_number(ticket_id) -> int:
    match = TICKET_ID_PATTERN.match(str(ticket_id).strip().upper())
    if not match:
        raise ValidationError(f"'{ticket_id}' is not a valid ticket ID.")
    return int(match.group(1))


def check_category(raw_category, allowed=None) -> str:
    options = list(get_known_categories() if allowed is None else allowed)
    return _check_choice(raw_category, options, "Category")


def check_urgency(raw_urgency) -> str:
    return _check_choice(raw_urgency, URGENCIES, "Urgency")


def check_status(raw_status) -> str:
    return _check_choice(raw_status, STATUSES, "Status")


def check_priority(raw_priority) -> str:
    return _check_choice(raw_priority, PRIORITIES, "Priority")


def check_affected_users(raw_affected_users) -> int:
    if isinstance(raw_affected_users, bool):
        raise ValidationError(
            "Affected users must be a whole number, not True/False."
        )
    if isinstance(raw_affected_users, float):
        raise ValidationError(
            "Affected users must be a whole number, not a decimal."
        )
    if isinstance(raw_affected_users, int):
        affected_users = raw_affected_users
    elif isinstance(raw_affected_users, str):
        try:
            affected_users = int(raw_affected_users.strip())
        except ValueError:
            raise ValidationError("Affected users must be a whole number.") from None
    else:
        raise ValidationError("Affected users must be a whole number.")

    if affected_users < 1:
        raise ValidationError("Affected users must be 1 or more.")
    return affected_users

def check_assigned_to(raw_assigned_to):
    if raw_assigned_to is None or raw_assigned_to is False:
        return None
    if isinstance(raw_assigned_to, str):
        label = raw_assigned_to.strip()
        return label or None
    raise ValidationError("An assignment must be a staff name.")

def check_note_id(raw_note_id) -> str:
    if not isinstance(raw_note_id, str):
        raise ValidationError("A note ID must be text.")
    cleaned = raw_note_id.strip().upper()
    if not NOTE_ID_PATTERN.match(cleaned):
        raise ValidationError(
            f"'{raw_note_id}' is not a valid note ID (expected N001, N002, ...)."
        )
    return cleaned

def check_note_author(raw_author) -> str:
    if not isinstance(raw_author, str):
        raise ValidationError("A note author must be text.")
    author = raw_author.strip()
    if not author:
        raise ValidationError("A note author cannot be blank.")
    return author


def check_note_message(raw_message) -> str:
    if not isinstance(raw_message, str):
        raise ValidationError("A note message must be text.")
    message = raw_message.strip()
    if len(message) < NOTE_MESSAGE_MIN_LENGTH:
        raise ValidationError(
            f"A note message must be at least {NOTE_MESSAGE_MIN_LENGTH} "
            "characters long."
        )
    if len(message) > NOTE_MESSAGE_MAX_LENGTH:
        raise ValidationError(
            f"A note message must be at most {NOTE_MESSAGE_MAX_LENGTH} "
            "characters long."
        )
    return message


def check_note(raw_note, ticket_id=None) -> dict:
    """Validate one note: exact keys, valid ID, non-blank author, sized message."""
    where = f" on ticket {ticket_id}" if ticket_id else ""
    if not isinstance(raw_note, dict):
        raise ValidationError(f"Each note{where} must be a JSON object.")

    missing = [key for key in NOTE_KEYS if key not in raw_note]
    if missing:
        raise ValidationError(
            f"A note{where} is missing: {', '.join(missing)}."
        )
    unexpected = [key for key in raw_note if key not in NOTE_KEYS]
    if unexpected:
        raise ValidationError(
            f"A note{where} has unexpected keys: {', '.join(sorted(unexpected))}."
        )

    return {
        "note_id": check_note_id(raw_note["note_id"]),
        "author": check_note_author(raw_note["author"]),
        "message": check_note_message(raw_note["message"]),
    }


def check_notes(raw_notes, ticket_id=None) -> list:
    """Validate a whole notes list, rejecting duplicate note IDs within it."""
    if raw_notes is None:
        return []
    if not isinstance(raw_notes, list):
        raise ValidationError(
            f"The notes field on ticket {ticket_id} must be a list."
        )

    notes = [check_note(note, ticket_id) for note in raw_notes]

    seen = set()
    for note in notes:
        if note["note_id"] in seen:
            raise ValidationError(
                f"Ticket {ticket_id} has a duplicate note ID {note['note_id']}."
            )
        seen.add(note["note_id"])
    return notes


@dataclass
class Ticket:
    id: str
    title: str
    category: str
    urgency: str
    affected_users: int
    priority: str
    status: str = "open"
    assigned_to: str | None = None
    notes: list = field(default_factory=list)

    def __post_init__(self):
        self.id = check_ticket_id(self.id)
        self.title = check_title(self.title)
        self.category = check_category(self.category)
        self.urgency = check_urgency(self.urgency)
        self.affected_users = check_affected_users(self.affected_users)
        self.priority = check_priority(self.priority)
        self.status = check_status(self.status)
        self.assigned_to = check_assigned_to(self.assigned_to)
        self.notes = check_notes(self.notes, self.id)

    @property
    def is_unresolved(self) -> bool:
        return self.status in NOTE_ALLOWED_STATUSES

    def can_receive_note(self) -> bool:
        return self.status in NOTE_ALLOWED_STATUSES
