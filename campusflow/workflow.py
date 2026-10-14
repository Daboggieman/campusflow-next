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


def move_ticket(ticket, new_status):
    current_status = ticket.status

    if new_status not in STATUS_MOVES.get(current_status, set()):
        raise ValueError(
            f"Cannot move ticket from {current_status} to {new_status}."
        )

    if new_status == "in_progress" and not ticket.assigned_to:
        raise ValueError("A ticket must be assigned before moving to in_progress.")

    ticket.status = new_status


def assign_ticket(ticket, staff_member):
    if ticket.status == "resolved":
        raise ValueError("A resolved ticket must be reopened before it can be assigned.")

    ticket.assigned_to = staff_member


def get_work_queue(tickets):
    active_tickets = [
        ticket
        for ticket in tickets.values()
        if ticket.status in {"open", "in_progress"}
    ]

    def sort_key(ticket):
        ticket_number = int(ticket.id[1:])
        return (
            PRIORITY_RANKS[ticket.priority],
            ticket_number,
        )

    return sorted(active_tickets, key=sort_key)
