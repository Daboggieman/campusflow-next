"""Structured follow-up notes.

This is the business/data layer for notes. It contains no ``input()`` and no
``print()``: the CLI owns the conversation, this module owns the rules.

The rule that shapes the whole module is **validate before mutate**. A note ID
is derived from the notes a ticket already has, and the ID is only computed
once every input has passed, so a rejected note cannot burn the next number.
That is what makes this sequence work:

    add N001 -> add N002 -> resolve -> attempt N003 (rejected) -> reopen
    -> add N003   # not N004

Notes are never removed by resolving or reopening, so a reopened ticket keeps
its history.
"""

from campusflow.errors import ValidationError
from campusflow.tickets import (
    NOTE_ALLOWED_STATUSES,
    check_note_author,
    check_note_message,
    check_ticket_id,
)


def notes_allowed(ticket) -> bool:
    """Whether a ticket may accept a new note right now."""
    return ticket.status in NOTE_ALLOWED_STATUSES


def note_id_number(note_id) -> int:
    """The numeric part of a note ID, for ordering."""
    return int(str(note_id).strip().upper()[1:])


def next_note_id(ticket) -> str:
    """The next free note ID for a ticket.

    Derived from the notes actually present rather than kept in a separate
    counter, so it cannot drift out of step with the file. If notes are N001
    and N003, the next one is N004; nothing is ever reused.
    """
    highest = max(
        (note_id_number(note["note_id"]) for note in ticket.notes),
        default=0,
    )
    return f"N{highest + 1:03d}"


def find_ticket(tickets, ticket_id):
    """Look a ticket up by ID, accepting a loosely typed ID. Raises if absent."""
    wanted = check_ticket_id(ticket_id)
    try:
        return tickets[wanted]
    except KeyError:
        raise ValidationError(f"Ticket {wanted} not found.") from None


def add_note(tickets, ticket_id, author, message) -> str:
    """Add one note and return its ID.

    Raises :class:`~campusflow.errors.ValidationError` — and changes nothing,
    including the note numbering — if the ticket is unknown, is resolved, or
    the author or message is unacceptable.
    """
    ticket = find_ticket(tickets, ticket_id)

    if not notes_allowed(ticket):
        raise ValidationError(
            f"Ticket {ticket.id} is {ticket.status}. A note can only be added "
            "to an open or in-progress ticket; reopen it first."
        )

    # Both of these raise before anything is written, so a bad message or a
    # blank author leaves the ticket byte-for-byte identical.
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
    """Every note for a ticket, in note ID order."""
    ticket = find_ticket(tickets, ticket_id)
    return sorted(ticket.notes, key=lambda note: note_id_number(note["note_id"]))
