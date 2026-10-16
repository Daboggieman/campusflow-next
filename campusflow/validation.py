"""Central validation helpers.

Field-level checks live next to the fields they police, in
:mod:`campusflow.tickets`. This module holds the checks that span more than one
record or that depend on the current category list, so that the CLI, the
storage layer and the note layer all reach for the *same* rule instead of each
writing their own.

The two error types are used deliberately:

* :class:`~campusflow.errors.ValidationError` — the user typed something the
  rules refuse. Show the message, re-prompt, change nothing.
* :class:`~campusflow.errors.DataError` — a stored record cannot be trusted.
  Abandon the whole load rather than accept part of it.
"""

from __future__ import annotations

from campusflow.categories import get_categories
from campusflow.errors import DataError, ValidationError
from campusflow.priority import calculate_priority
from campusflow.tickets import (
    PRIORITIES,
    STATUSES,
    URGENCIES,
    Ticket,
    check_category,
    check_priority,
    check_status,
    check_urgency,
)

#: Every stored ticket must carry these.
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

#: ``notes`` is written out but not required on the way in, so a file saved by
#: the first version of CampusFlow still loads.
OPTIONAL_TICKET_KEYS = ("notes",)


def validate_new_category(raw_category) -> str:
    """Validate a category for a ticket being created or edited.

    Stricter than :func:`campusflow.tickets.check_category`: only *active*
    categories are accepted, so a retired one can never be chosen for new work.
    Existing tickets carrying a retired category still load — that check uses
    the wider known set.
    """
    return check_category(raw_category, allowed=get_categories())


def validate_ticket_record(key, record) -> Ticket:
    """Validate one stored record and return the ``Ticket`` it describes.

    Checks, in order: the record is an object; required keys are present; no
    unexpected keys; every field passes its own check; the record's ``id``
    agrees with the key it is filed under; and the stored ``priority`` is the
    one the priority rules actually imply for that urgency and user count.

    The priority check is the strictest one here. It is what makes a
    hand-edited priority visible instead of silently wrong, and it is why a
    record must be consistent before it can be loaded at all.
    """
    if not isinstance(record, dict):
        raise DataError(f"Ticket {key} must be a JSON object.")

    missing = [name for name in REQUIRED_TICKET_KEYS if name not in record]
    if missing:
        raise DataError(
            f"Ticket {key} is missing required field(s): {', '.join(missing)}."
        )

    unexpected = [
        name
        for name in record
        if name not in REQUIRED_TICKET_KEYS and name not in OPTIONAL_TICKET_KEYS
    ]
    if unexpected:
        raise DataError(
            f"Ticket {key} has unexpected field(s): "
            f"{', '.join(sorted(unexpected))}."
        )

    try:
        ticket = Ticket(**record)
    except ValidationError as error:
        raise DataError(f"Ticket {key} is invalid: {error}") from error

    if ticket.id != key:
        raise DataError(
            f"Ticket key {key} does not match its stored ID {ticket.id}."
        )

    expected_priority = calculate_priority(ticket.urgency, ticket.affected_users)
    if ticket.priority != expected_priority:
        raise DataError(
            f"Ticket {key} stores priority '{ticket.priority}', but urgency "
            f"'{ticket.urgency}' with {ticket.affected_users} affected users "
            f"implies '{expected_priority}'. Correct the record, or start "
            "fresh to rebuild the file."
        )

    return ticket


def validate_ticket_collection(data, source="tickets") -> dict:
    """Validate a whole decoded collection, or raise and return nothing.

    The caller gets a fully built dictionary only when **every** record passed.
    There is no partial result, which is what allows the caller to keep its
    existing in-memory tickets untouched after a bad load.
    """
    if not isinstance(data, dict):
        raise DataError(f"{source} must contain a JSON object keyed by ticket ID.")

    tickets = {}
    for key, record in data.items():
        tickets[key] = validate_ticket_record(key, record)
    return tickets


def validate_search_filters(category=None, status=None, priority=None) -> dict:
    """Normalise search filters, treating blank as "do not filter on this".

    Used by the CLI so an unknown option re-prompts instead of quietly
    returning an empty result list.
    """
    return {
        "category": _normalise_filter(category, check_category, "category"),
        "status": _normalise_filter(status, check_status, "status"),
        "priority": _normalise_filter(priority, check_priority, "priority"),
    }


def _normalise_filter(raw_value, check, label):
    if raw_value is None:
        return None
    if isinstance(raw_value, str) and not raw_value.strip():
        return None
    try:
        return check(raw_value)
    except ValidationError as error:
        raise ValidationError(f"Invalid {label} filter: {error}") from None


def describe_allowed_values() -> dict:
    """The legal values, for prompts and help text in one place."""
    return {
        "categories": list(get_categories()),
        "urgencies": list(URGENCIES),
        "statuses": list(STATUSES),
        "priorities": list(PRIORITIES),
    }
