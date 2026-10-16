"""Ticket lifecycle: status moves, assignment, and the Open Work Queue."""

from campusflow.errors import ValidationError
from campusflow.tickets import (
    check_assigned_to,
    check_status,
    ticket_number,
)

#: The only status moves the app allows. Every other move is refused.
STATUS_MOVES = {
    "open": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"open"},
}

PRIORITY_RANKS = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def can_transition(current_status, new_status) -> bool:
    """Whether ``current_status`` may legally become ``new_status``.

    Pure predicate: it answers the question without touching a ticket, so it
    can be used by a menu to grey out an option as well as by
    :func:`move_ticket` to enforce the rule.
    """
    return new_status in STATUS_MOVES.get(current_status, set())


def move_ticket(ticket, new_status):
    """Change a ticket's status, or refuse and leave it exactly as it was.

    The ticket is only written to once every rule has passed, so a rejected
    move cannot leave a half-changed record behind.
    """
    wanted = check_status(new_status)
    current_status = ticket.status

    if not can_transition(current_status, wanted):
        raise ValidationError(
            f"Cannot move ticket from {current_status} to {wanted}."
        )

    if wanted == "in_progress" and not ticket.assigned_to:
        raise ValidationError(
            "A ticket must be assigned before moving to in_progress."
        )

    ticket.status = wanted


def assign_ticket(ticket, staff_member):
    """Assign a ticket to a staff label.

    Refused on a resolved ticket, which must be reopened first. That rule is
    why a resolved ticket cannot be re-assigned behind the scenes.
    """
    if ticket.status == "resolved":
        raise ValidationError(
            "A resolved ticket must be reopened before it can be assigned."
        )

    ticket.assigned_to = check_assigned_to(staff_member)


def get_work_queue(tickets):
    """The Original Open Work Queue: everything not yet resolved.

    Behaviour is deliberately unchanged from the first version — open **and**
    in_progress tickets, sorted by priority rank and then by numeric ticket
    number so ``T100`` does not sort before ``T20``.
    """

    def sort_key(ticket):
        return (PRIORITY_RANKS[ticket.priority], ticket_number(ticket.id))

    active_tickets = [
        ticket
        for ticket in tickets.values()
        if ticket.status in ("open", "in_progress")
    ]
    return sorted(active_tickets, key=sort_key)
