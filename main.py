from campusflow.priority import calculate_priority
from campusflow.tickets import categories, urgencies, Ticket
from campusflow.storage import generate_ticket_id, load_application_data, save_tickets
from campusflow.workflow import move_ticket, assign_ticket, get_work_queue
from campusflow.reports import generate_report, print_report

tickets = {}
counter = 0
staff = []


def create_ticket():
    global tickets, counter
    while True:
        title = input("enter title: ").strip().lower()
        if title:
            break
        print("title cannot be empty")
    while True:
        category = input("enter category [network, hardware, software, administrative, other]: ").strip().lower()
        if category in categories:
            break
        print("Invalid category")
    while True:
        urgency = input("enter urgency [low, medium, high]: ").strip().lower()
        if urgency in urgencies:
            break
        print("Invalid urgency")
    while True:
        try:
            affected_users = int(input("enter affected users: "))
            if affected_users > 0:
                break
            print("enter a number greater than zero.")
        except ValueError:
            print("enter a whole number.")
    priority = calculate_priority(urgency, affected_users)
    ticket_id, next_counter = generate_ticket_id(counter)
    counter = next_counter
    ticket = Ticket(
        id=ticket_id,
        title=title,
        category=category,
        urgency=urgency,
        affected_users=affected_users,
        priority=priority,
        status="open",
        assigned_to=False,
    )
    tickets[ticket_id] = ticket
    save_tickets(tickets)
    print(f"Ticket created: {ticket_id} - {ticket.title} ")
    print("-------------------------------------------- \n")


def list_ticket():
    if not tickets:
        print("No tickets yet.")
        return
    for ticket in tickets.values():
        print(ticket.id, ticket.title, ticket.priority, ticket.status)
    ticket_id = input("enter ticket ID to view: ").strip().upper()
    if ticket_id not in tickets:
        print("Ticket not found.")
        return
    ticket = tickets[ticket_id]
    print(f"id: {ticket.id}")
    print(f"title: {ticket.title}")
    print(f"category: {ticket.category}")
    print(f"urgency: {ticket.urgency}")
    print(f"affected users: {ticket.affected_users}")
    print(f"priority: {ticket.priority}")
    print(f"status: {ticket.status}")
    print(f"assigned to: {ticket.assigned_to}")
    print("-------------------------------------------- \n")

def assign():
    if not tickets:
        print("No tickets to assign.")
        return
    if not staff:
        print("No staff available.")
        return
    ticket_id = input("enter ticket ID to assign: ").strip().upper()
    if ticket_id not in tickets:
        print("Ticket not found.")
        return
    print("Available staff:")
    for index, name in enumerate(staff, start=1):
        print(f"{index}. {name}")
    try:
        choice = int(input("choose a staff member: "))
    except ValueError:
        print("Invalid staff selection.")
        return
    if not 1 <= choice <= len(staff):
        print("Invalid staff selection.")
        return
    try:
        assign_ticket(tickets[ticket_id], staff[choice - 1])
        save_tickets(tickets)
        print(f"Ticket {ticket_id} assigned to {staff[choice - 1]}.")
        print("-------------------------------------------- \n")
    except ValueError as error:
        print(error)



def change_status():
    if not tickets:
        print("No tickets to update.")
        return
    ticket_id = input("enter ticket ID to change status: ").strip().upper()
    if ticket_id not in tickets:
        print("Ticket not found.")
        return
    new_status = input("enter new status (open, in_progress, resolved): ").strip().lower()
    try:
        move_ticket(tickets[ticket_id], new_status)
        save_tickets(tickets)
        print(f"Ticket {ticket_id} is now {new_status}.")
        print("-------------------------------------------- \n")

    except ValueError as error:
        print(error)


def work_queue():
    queue = get_work_queue(tickets)
    if not queue:
        print("No open or in-progress tickets.")
        return
    for ticket in queue:
        print(ticket.id, ticket.priority, ticket.status)
        print("-------------------------------------------- \n")



def reports():
    print_report(generate_report(tickets))
    print("-------------------------------------------- \n")



def quit_program():
    return


def main():
    global tickets, counter, staff
    tickets, counter, staff = load_application_data()
    while True:
        for number, (label, action) in enumerate(menu, start=1):
            print(f"{number}. {label}")
        choice = input("choose an option: ")
        try:
            choice = int(choice)
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


menu = [
    ("create ticket", create_ticket),
    ("list tickets", list_ticket),
    ("assign ticket", assign),
    ("change status", change_status),
    ("work queue", work_queue),
    ("reports", reports),
    ("quit", quit_program),
]

if __name__ == "__main__":
    main()
