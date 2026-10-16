"""CampusFlow Next — the command-line interface.

This module is glue. Every rule it enforces lives in a module that can be
tested without typing at a prompt:

===========================  ===========================================
campusflow.tickets           the record and its field checks
campusflow.validation        the checks that span records, incl. load
campusflow.workflow          status moves, assignment, the Open Work Queue
campusflow.notes             follow-up notes, validate-before-mutate
campusflow.search            read-only search and filtering
campusflow.reports           the report numbers and their display
campusflow.storage           loading, saving, ID continuity
campusflow.categories        the editable category list
campusflow.understanding_check  the question bank and its scoring
===========================  ===========================================

So the loops here only do three things: read input, call one of those
functions, and print what came back. A rejected action shows a message and
returns to the menu, and because the underlying functions validate before they
write, nothing is half-changed when that happens.
"""

from pathlib import Path

from campusflow import categories, notes, storage
from campusflow.errors import DataError, ValidationError
from campusflow.priority import calculate_priority
from campusflow.reports import generate_report, print_report
from campusflow.search import (
    describe_filters,
    search_tickets,
    sort_by_priority_then_id,
)
from campusflow.tickets import (
    PRIORITIES,
    STATUSES,
    URGENCIES,
    Ticket,
    check_affected_users,
    check_category,
    check_priority,
    check_status,
    check_title,
    check_urgency,
    ticket_number,
)
from campusflow.validation import (
    validate_new_category,
    validate_search_filters,
)
from campusflow.workflow import assign_ticket, get_work_queue, move_ticket

UNDERSTANDING_NOTES_PATH = Path("docs/understanding-notes.md")


class AppState:
    """What the app holds in memory between menu choices."""

    def __init__(self):
        self.tickets = {}
        self.counter = 0
        self.staff = []
        self.warnings = []


state = AppState()


def report_problem(error) -> None:
    """Show a rejected action without ending the program."""
    print(f"Not done: {error}")


def ask(prompt):
    return input(prompt)


def ask_validated(prompt, check):
    """Ask until ``check`` accepts the answer, showing why each try failed."""
    while True:
        try:
            return check(ask(prompt))
        except ValidationError as error:
            print(error)


def ask_filter(prompt, allowed, field):
    """Ask for one search filter.

    Blank means "do not filter on this field". Anything else goes through the
    shared :func:`validate_search_filters` helper, so an unrecognised option
    re-prompts here instead of quietly matching nothing.
    """
    while True:
        raw = ask(prompt)
        if not raw.strip():
            return None
        try:
            return validate_search_filters(**{field: raw})[field]
        except ValidationError:
            print(f"Choose one of: {', '.join(allowed)}, or press Enter to skip.")


def ask_ticket_id(prompt):
    while True:
        ticket_id = ask(prompt).strip().upper()
        if ticket_id in state.tickets:
            return ticket_id
        print(f"Ticket {ticket_id or '(blank)'} not found.")


def save():
    storage.save_tickets(state.tickets)


# --------------------------------------------------------------------------
# tickets
# --------------------------------------------------------------------------


def create_ticket():
    title = ask_validated("enter title: ", check_title)
    category = ask_validated(
        f"enter category [{', '.join(categories.get_categories())}]: ",
        validate_new_category,
    )
    urgency = ask_validated(
        f"enter urgency [{', '.join(URGENCIES)}]: ",
        check_urgency,
    )
    affected_users = ask_validated("enter affected users: ", check_affected_users)

    priority = calculate_priority(urgency, affected_users)

    # The ID is previewed but not committed: if the ticket somehow fails to
    # build, the counter is untouched and no ID is burned.
    ticket_id, next_counter = storage.next_ticket_id(state.counter)

    try:
        ticket = Ticket(
            id=ticket_id,
            title=title,
            category=category,
            urgency=urgency,
            affected_users=affected_users,
            priority=priority,
            status="open",
            assigned_to=None,
        )
    except ValidationError as error:
        report_problem(error)
        return

    storage.save_counter(next_counter)
    state.counter = next_counter
    state.tickets[ticket_id] = ticket
    save()
    print(f"Ticket created: {ticket_id} - {ticket.title}")
    print(f"priority {ticket.priority}, status {ticket.status}")
    print("-------------------------------------------- \n")


def list_ticket():
    if not state.tickets:
        print("No tickets yet.")
        return
    for ticket in sorted(state.tickets.values(), key=_ticket_sort_key):
        print(ticket.id, ticket.title, ticket.priority, ticket.status)

    ticket_id = ask("enter ticket ID to view: ").strip().upper()
    if ticket_id not in state.tickets:
        print("Ticket not found.")
        return
    show_ticket(state.tickets[ticket_id])


def show_ticket(ticket):
    print(f"id: {ticket.id}")
    print(f"title: {ticket.title}")
    print(f"category: {ticket.category}")
    print(f"urgency: {ticket.urgency}")
    print(f"affected users: {ticket.affected_users}")
    print(f"priority: {ticket.priority}")
    print(f"status: {ticket.status}")
    print(f"assigned to: {ticket.assigned_to or 'unassigned'}")
    print(f"notes: {len(ticket.notes)}")
    print("-------------------------------------------- \n")


def assign():
    if not state.tickets:
        print("No tickets to assign.")
        return
    if not state.staff:
        print("No staff available.")
        return

    ticket_id = ask_ticket_id("enter ticket ID to assign: ")

    print("Available staff:")
    for index, name in enumerate(state.staff, start=1):
        print(f"{index}. {name}")
    try:
        choice = int(ask("choose a staff member: "))
    except ValueError:
        print("Invalid staff selection.")
        return
    if not 1 <= choice <= len(state.staff):
        print("Invalid staff selection.")
        return

    try:
        assign_ticket(state.tickets[ticket_id], state.staff[choice - 1])
    except ValidationError as error:
        report_problem(error)
        return

    save()
    print(f"Ticket {ticket_id} assigned to {state.staff[choice - 1]}.")
    print("-------------------------------------------- \n")


def change_status():
    if not state.tickets:
        print("No tickets to update.")
        return

    ticket_id = ask_ticket_id("enter ticket ID to change status: ")
    new_status = ask_validated(
        f"enter new status ({', '.join(STATUSES)}): ", check_status
    )

    try:
        move_ticket(state.tickets[ticket_id], new_status)
    except ValidationError as error:
        report_problem(error)
        return

    save()
    print(f"Ticket {ticket_id} is now {new_status}.")
    print("-------------------------------------------- \n")


def work_queue():
    """The Original Open Work Queue. Unchanged from the first version."""
    queue = get_work_queue(state.tickets)
    if not queue:
        print("No open or in-progress tickets.")
        return
    for ticket in queue:
        print(ticket.id, ticket.priority, ticket.status)
        print("-------------------------------------------- \n")


# --------------------------------------------------------------------------
# notes
# --------------------------------------------------------------------------


def add_follow_up_note():
    if not state.tickets:
        print("No tickets yet.")
        return

    ticket_id = ask_ticket_id("enter ticket ID to add a note to: ")
    author = ask("note author: ")
    message = ask(f"note message ({5}-{300} characters): ")

    try:
        note_id = notes.add_note(state.tickets, ticket_id, author, message)
    except ValidationError as error:
        report_problem(error)
        return

    save()
    print(f"Note {note_id} added to {ticket_id}.")
    print("-------------------------------------------- \n")


def view_ticket_notes():
    if not state.tickets:
        print("No tickets yet.")
        return

    ticket_id = ask_ticket_id("enter ticket ID to view notes for: ")
    try:
        ticket_notes = notes.get_notes(state.tickets, ticket_id)
    except ValidationError as error:
        report_problem(error)
        return

    if not ticket_notes:
        print(f"Ticket {ticket_id} has no notes yet.")
        return

    print(f"Notes for {ticket_id}:")
    for note in ticket_notes:
        print(f"  {note['note_id']} [{note['author']}] {note['message']}")
    print("-------------------------------------------- \n")


# --------------------------------------------------------------------------
# search
# --------------------------------------------------------------------------


def _run_search():
    """Ask for filters and return the matching tickets, in ticket ID order."""
    title = ask("title contains (blank for any): ")

    category = ask_filter(
        f"category [{', '.join(categories.get_categories())}] (blank for any): ",
        categories.get_categories(),
        "category",
    )
    status = ask_filter(
        f"status [{', '.join(STATUSES)}] (blank for any): ", STATUSES, "status"
    )
    priority = ask_filter(
        f"priority [{', '.join(PRIORITIES)}] (blank for any): ",
        PRIORITIES,
        "priority",
    )

    print(f"Searching: {describe_filters(title, category, status, priority)}")

    return search_tickets(
        state.tickets,
        title=title,
        category=category,
        status=status,
        priority=priority,
    )


def _print_search_results(results):
    if not results:
        print("No tickets matched.")
        return
    for ticket in results:
        print(
            f"{ticket.id} | {ticket.title} | {ticket.category} | "
            f"{ticket.priority} | {ticket.status} | "
            f"{ticket.assigned_to or 'unassigned'}"
        )
    print(f"{len(results)} ticket(s) matched.")
    print("-------------------------------------------- \n")


def search():
    _print_search_results(_run_search())


def search_by_priority():
    """The separate optional view: search results ordered by priority then ID."""
    _print_search_results(sort_by_priority_then_id(_run_search()))


# --------------------------------------------------------------------------
# reports and categories
# --------------------------------------------------------------------------


def reports():
    print_report(generate_report(state.tickets))
    print("-------------------------------------------- \n")


def manage_categories():
    while True:
        print("\nCategories")
        print(f"  active:  {', '.join(categories.get_categories())}")
        retired = categories.get_retired_categories()
        print(f"  retired: {', '.join(retired) if retired else '(none)'}")
        print("1. add a category")
        print("2. retire a category")
        print("3. back to the main menu")

        choice = ask("choose an option: ").strip()
        if choice == "3":
            return
        if choice == "1":
            try:
                name = categories.add_category(ask("new category name: "))
            except ValidationError as error:
                report_problem(error)
                continue
            categories.save_categories(storage.CATEGORIES_FILE)
            print(f"Category '{name}' added.")
        elif choice == "2":
            try:
                name = categories.retire_category(ask("category to retire: "))
            except ValidationError as error:
                report_problem(error)
                continue
            categories.save_categories(storage.CATEGORIES_FILE)
            print(
                f"Category '{name}' retired. Tickets already using it still "
                "load and display."
            )
        else:
            print("Invalid menu option.")


def understanding_check():
    from campusflow.understanding_check import run_check

    result = run_check(save_path=UNDERSTANDING_NOTES_PATH)
    print(f"Final score: {result['score']}/{result['total']}")


def quit_program():
    return None


# --------------------------------------------------------------------------
# menu
# --------------------------------------------------------------------------


def _ticket_sort_key(ticket):
    return ticket_number(ticket.id)


menu = [
    ("create ticket", create_ticket),
    ("list tickets", list_ticket),
    ("assign ticket", assign),
    ("change status", change_status),
    ("open work queue", work_queue),
    ("add follow-up note", add_follow_up_note),
    ("view ticket notes", view_ticket_notes),
    ("search tickets", search),
    ("search tickets by priority", search_by_priority),
    ("reports", reports),
    ("manage categories", manage_categories),
    ("engineering understanding check", understanding_check),
    ("quit", quit_program),
]


# --------------------------------------------------------------------------
# startup
# --------------------------------------------------------------------------


def start_fresh():
    """Back up whatever is unusable and begin from an empty, valid dataset."""
    for path in (
        storage.TICKETS_FILE,
        storage.COUNTER_FILE,
        storage.CATEGORIES_FILE,
    ):
        storage.backup_broken_file(path)

    categories.reset_categories()
    storage.save_tickets({})
    storage.save_counter(0)
    categories.save_categories(storage.CATEGORIES_FILE)
    return storage.load_application_data()


def load_or_offer_fresh_start():
    while True:
        try:
            return storage.load_application_data()
        except DataError as error:
            print(f"\nError loading data: {error}")
            choice = ask("Enter 'q' to quit or 'f' to start fresh: ").strip().lower()
            if choice == "q":
                raise SystemExit("Application terminated.")
            if choice == "f":
                try:
                    return start_fresh()
                except DataError as fresh_error:
                    print(f"Could not start fresh: {fresh_error}")
                    continue
            print("Invalid choice. Enter 'q' or 'f'.")


def main():
    data = load_or_offer_fresh_start()

    state.tickets = data.tickets
    state.counter = data.counter
    state.staff = data.staff
    state.warnings = data.warnings

    for warning in state.warnings:
        print(f"WARNING: {warning}")

    while True:
        print()
        for number, (label, _action) in enumerate(menu, start=1):
            print(f"{number}. {label}")

        raw_choice = ask("choose an option: ")
        try:
            choice = int(raw_choice)
        except ValueError:
            print("Enter a valid menu number.")
            continue

        if not 1 <= choice <= len(menu):
            print("Invalid menu option.")
            continue

        action = menu[choice - 1][1]
        action()
        if action is quit_program:
            break


if __name__ == "__main__":
    main()
