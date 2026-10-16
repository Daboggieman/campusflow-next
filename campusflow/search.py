from campusflow.tickets import ticket_number
from campusflow.workflow import PRIORITY_RANKS

def _matches_text(haystack, needle) -> bool:
    return needle.casefold() in haystack.casefold()

def _matches_field(value, wanted) -> bool:
    return value.casefold() == wanted.strip().casefold()

def search_tickets(tickets, title="", category=None, status=None, priority=None):
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
    return sorted(
        tickets,
        key=lambda ticket: (PRIORITY_RANKS[ticket.priority], ticket_number(ticket.id)),
    )

def describe_filters(title="", category=None, status=None, priority=None) -> str:
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
