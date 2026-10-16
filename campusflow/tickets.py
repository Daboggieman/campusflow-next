"""The ticket record and the field checks that police it.

Design rule carried over from the original project: the field checks live in
small functions that take the *rawest* possible input, clean it, and return the
correctly-typed value. The dataclass calls them in ``__post_init__``, so a
half-valid ``Ticket`` can never be constructed. Callers raise rather than
returning a "failed" flag, which is what makes "a bad ticket can never be
created" true.

What changed in CampusFlow Next and why:

* ``check_affected_users`` used to accept anything :func:`int` accepted. Since
  ``int(True) == 1`` and ``int(3.7) == 3`` in Python, booleans and floats
  slipped through as valid counts. Both are now rejected explicitly.
* ``status`` and ``priority`` were never checked at all, so a hand-edited JSON
  file could load a ticket in status ``"banana"``. Both are now validated.
* ``assigned_to`` was ``False`` when unassigned and a string once assigned.
  It is now ``None`` or a non-empty label, and the old ``False`` is still
  accepted on load so existing files keep working.
* ``notes`` is new. It is validated on construction, so notes coming from disk
  get exactly the same scrutiny as notes typed at the prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from campusflow.categories import get_known_categories
from campusflow.errors import ValidationError

#: Urgency no longer includes "critical". "critical" is a *priority*, and
#: having it in both lists was a trap; no shipped ticket or test used it.
URGENCIES = ("low", "medium", "high")
STATUSES = ("open", "in_progress", "resolved")
PRIORITIES = ("critical", "high", "medium", "low")

#: Statuses that may receive a new follow-up note or an assignment change.
NOTE_ALLOWED_STATUSES = ("open", "in_progress")

NOTE_MESSAGE_MIN_LENGTH = 5
NOTE_MESSAGE_MAX_LENGTH = 300

#: ``T`` followed by digits. Leading zeros are tolerated (T020) because the
#: original project and its tests both produce them.
TICKET_ID_PATTERN = re.compile(r"^T(\d+)$")

#: ``N`` followed by at least three digits: N001, N002, ... N1000.
NOTE_ID_PATTERN = re.compile(r"^N(\d{3,})$")

NOTE_KEYS = ("note_id", "author", "message")


def _check_choice(raw_value, allowed, label):
    """Shared body of the enumerable field checks."""
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
    """Trim a title and reject one that is blank once trimmed.

    The original stores titles lowercased; search matches case-insensitively
    either way, so that behaviour is kept.
    """
    if not isinstance(raw_title, str):
        raise ValidationError("Title must be text.")
    title = raw_title.strip().lower()
    if not title:
        raise ValidationError("Title cannot be blank.")
    return title


def check_ticket_id(raw_id) -> str:
    """A ticket ID must look like ``T`` followed by a positive number."""
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
    """The numeric part of a ticket ID, for sorting and counting.

    Sorting on the number rather than the text is what stops ``T100`` coming
    before ``T20``. Raises rather than guessing if the ID is malformed, because
    every ``Ticket`` has already been through :func:`check_ticket_id`.
    """
    match = TICKET_ID_PATTERN.match(str(ticket_id).strip().upper())
    if not match:
        raise ValidationError(f"'{ticket_id}' is not a valid ticket ID.")
    return int(match.group(1))


def check_category(raw_category, allowed=None) -> str:
    """Return the stored spelling of a category.

    ``allowed`` defaults to the categories the app *knows*, which is the active
    list plus anything retired. That is deliberately more permissive than the
    create prompt, so retiring a category never makes an existing ticket
    unloadable. New input is checked against the active list by
    :func:`campusflow.validation.validate_new_category`.
    """
    options = list(get_known_categories() if allowed is None else allowed)
    return _check_choice(raw_category, options, "Category")


def check_urgency(raw_urgency) -> str:
    return _check_choice(raw_urgency, URGENCIES, "Urgency")


def check_status(raw_status) -> str:
    return _check_choice(raw_status, STATUSES, "Status")


def check_priority(raw_priority) -> str:
    return _check_choice(raw_priority, PRIORITIES, "Priority")


def check_affected_users(raw_affected_users) -> int:
    """A strictly positive whole number of users.

    Booleans are rejected before the ``int`` branch is reached, because
    ``isinstance(True, int)`` is true and ``True`` would otherwise become 1.
    Floats are rejected rather than truncated, so 3.7 cannot quietly mean 3.
    """
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
    """Normalise the assignment field to ``None`` or a non-empty label.

    ``False`` (what the original project wrote for "nobody") and blank strings
    both mean unassigned, so old files keep loading. Anything else that is not
    a string is a data error rather than a silent coercion.
    """
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
    """Trim a note message and hold it to 5-300 characters."""
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
    """One support ticket.

    ``notes`` defaults to an empty list so that every ticket in a file written
    before CampusFlow Next still loads. ``status`` and ``assigned_to`` also
    default, so a caller that only cares about the core fields can omit them.
    """

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
        """Open or in progress. Resolved tickets are the only settled ones."""
        return self.status in NOTE_ALLOWED_STATUSES

    def can_receive_note(self) -> bool:
        return self.status in NOTE_ALLOWED_STATUSES
