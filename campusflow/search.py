"""Read-only search and filtering.

Nothing in this module writes to a ticket, and nothing in it prints. Both
properties are deliberate: the CLI can call it freely knowing a search cannot
corrupt data, and the functions can be tested by comparing returned lists
rather than by capturing output.

Filter semantics, which the brief is explicit about: **if a filter is supplied
it must match, so several filters together are AND, not OR.** A blank or
``None`` filter means "do not filter on this field" rather than "match
nothing".
"""

from campusflow.tickets import ticket_number
from campusflow.workflow import PRIORITY_RANKS


def _matches_text(haystack, needle) -> bool:
    """Case-insensitive substring test.

    ``casefold`` rather than ``lower``: it handles the case mappings that are
    not one-to-one, so ``"STRASSE"`` finds a title stored as ``"Straße"``
    (``"ß".lower()`` is ``"ß"``, but ``"ß".casefold()`` is ``"ss"``). ``lower``
    would miss it.
    """
    return needle.casefold() in haystack.casefold()


def _matches_field(value, wanted) -> bool:
    return value.casefold() == wanted.strip().casefold()


def search_tickets(tickets, title="", category=None, status=None, priority=None):
    """Return the tickets matching every supplied filter, in ticket ID order.

    Results are sorted by the *numeric* ticket number, so the order is stable
    and ``T100`` does not sort before ``T20``. Dictionary iteration order is
    never relied on.
    """
    title_query = (title or "").strip()

    results = []
    for ticket in tickets.values():
        if title_query and not _matches_text(ticket.title, title_query):
            continue
        if category and not _matches_field(ticket.category, category):
            continue
        if status and not _matches_field(ticket.status, status):
            continue
        if priority and not _matches_field(ticket.priority, priority):
            continue
        results.append(ticket)

    return sorted(results, key=lambda ticket: ticket_number(ticket.id))


def sort_by_priority_then_id(tickets):
    """Order tickets by priority (critical first) and then by ticket ID.

    This backs the *separate* optional view required alongside the Original
    Open Work Queue — the queue itself is left exactly as it was.
    """
    return sorted(
        tickets,
        key=lambda ticket: (PRIORITY_RANKS[ticket.priority], ticket_number(ticket.id)),
    )


def describe_filters(title="", category=None, status=None, priority=None) -> str:
    """A short human-readable summary of what a search actually applied."""
    parts = []
    if (title or "").strip():
        parts.append(f"title contains '{title.strip()}'")
    if category:
        parts.append(f"category is {category}")
    if status:
        parts.append(f"status is {status}")
    if priority:
        parts.append(f"priority is {priority}")
    return " and ".join(parts) if parts else "no filters (all tickets)"
