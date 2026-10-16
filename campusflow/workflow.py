from campusflow.errors import ValidationError
from campusflow.tickets import (
    check_assigned_to,
    check_status,
    ticket_number,
)
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
    return new_status in STATUS_MOVES.get(current_status, set())


def move_ticket(ticket, new_status):
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
    if ticket.status == "resolved":
        raise ValidationError(
            "A resolved ticket must be reopened before it can be assigned."
        )

    ticket.assigned_to = check_assigned_to(staff_member)


def get_work_queue(tickets):
    def sort_key(ticket):
        return (PRIORITY_RANKS[ticket.priority], ticket_number(ticket.id))

    active_tickets = [
        ticket
        for ticket in tickets.values()
        if ticket.status in ("open", "in_progress")
    ]
    return sorted(active_tickets, key=sort_key)
