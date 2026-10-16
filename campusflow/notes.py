from campusflow.errors import ValidationError
from campusflow.tickets import (
    NOTE_ALLOWED_STATUSES,
    check_note_author,
    check_note_message,
    check_ticket_id,
)


def notes_allowed(ticket) -> bool:
    return ticket.status in NOTE_ALLOWED_STATUSES


def note_id_number(note_id) -> int:
    return int(str(note_id).strip().upper()[1:])


def next_note_id(ticket) -> str:
    highest = max(
        (note_id_number(note["note_id"]) for note in ticket.notes),
        default=0,
    )
    return f"N{highest + 1:03d}"


def find_ticket(tickets, ticket_id):
    wanted = check_ticket_id(ticket_id)
    try:
        return tickets[wanted]
    except KeyError:
        raise ValidationError(f"Ticket {wanted} not found.") from None

def add_note(tickets, ticket_id, author, message) -> str:
    ticket = find_ticket(tickets, ticket_id)
    if not notes_allowed(ticket):
        raise ValidationError(
            f"Ticket {ticket.id} is {ticket.status}. A note can only be added "
            "to an open or in-progress ticket; reopen it first."
        )

    clean_author = check_note_author(author)
    clean_message = check_note_message(message)
    note_id = next_note_id(ticket)
    ticket.notes.append(
        {
            "note_id": note_id,
            "author": clean_author,
            "message": clean_message,
        }
    )
    return note_id

def get_notes(tickets, ticket_id) -> list:
    ticket = find_ticket(tickets, ticket_id)
    return sorted(ticket.notes, key=lambda note: note_id_number(note["note_id"]))
