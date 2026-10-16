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
OPTIONAL_TICKET_KEYS = ("notes",)


def validate_new_category(raw_category) -> str:
    return check_category(raw_category, allowed=get_categories())


def validate_ticket_record(key, record) -> Ticket:
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
    if not isinstance(data, dict):
        raise DataError(f"{source} must contain a JSON object keyed by ticket ID.")

    tickets = {}
    for key, record in data.items():
        tickets[key] = validate_ticket_record(key, record)
    return tickets

def validate_search_filters(category=None, status=None, priority=None) -> dict:
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
    return {
        "categories": list(get_categories()),
        "urgencies": list(URGENCIES),
        "statuses": list(STATUSES),
        "priorities": list(PRIORITIES),
    }
