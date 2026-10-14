import json
import shutil
from dataclasses import asdict
from pathlib import Path
from campusflow.tickets import Ticket


DATA_DIR = Path("data_folder")
TICKETS_FILE = DATA_DIR / "tickets.json"
COUNTER_FILE = DATA_DIR / "counter.json"
STAFF_FILE = DATA_DIR / "staff.json"

DEFAULT_STAFF = [
    "Mr. Kingsley(HOC)",
    "Mr. Godswill",
    "Mr. Izzy",
    "Mr. Gabriel",
    "Mr. Emmanuel",
    "Mr. Ayuba"
]


def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not TICKETS_FILE.exists():
        save_tickets({})

    if not COUNTER_FILE.exists():
        save_counter(0)

    if not STAFF_FILE.exists():
        save_staff(DEFAULT_STAFF.copy())

def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def load_tickets():
    if not TICKETS_FILE.exists():
        return {}
    try:
        data = load_json(TICKETS_FILE)

        if not isinstance(data, dict):
            raise ValueError("The tickets file must contain a valid JSON object.")
        tickets = {}

        for ticket_id, ticket_data in data.items():
            if not isinstance(ticket_data, dict):
                raise ValueError(
                    f"Ticket {ticket_id} must contain a JSON object."
                )

            ticket = Ticket(**ticket_data)

            if ticket.id != ticket_id:
                raise ValueError(
                    f"Ticket key {ticket_id} does not match "
                    f"its stored ID {ticket.id}."
                )

            tickets[ticket_id] = ticket

        return tickets

    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
        print(f"\nError loading tickets: {error}")

        while True:
            choice = input(
                "Enter 'q' to quit or 'f' to start fresh: "
            ).strip().lower()

            if choice == "q":
                raise SystemExit("Application terminated.")

            if choice == "f":
                backup_broken_file(TICKETS_FILE)
                save_tickets({})
                return {}

            print("Invalid choice. Enter 'q' or 'f'.")


def backup_broken_file(path):
    if not path.exists():
        return

    backup_path = path.with_suffix(".json.bak")
    counter = 1

    while backup_path.exists():
        backup_path = path.with_suffix(f".json.bak.{counter}")
        counter += 1

    shutil.copy2(path, backup_path)

    print(f"Backup created: {backup_path}")

def save_tickets(tickets):
    data = {
        ticket_id: asdict(ticket)
        for ticket_id, ticket in tickets.items()
    }
    save_json(TICKETS_FILE, data)

def load_counter():
    if not COUNTER_FILE.exists():
        return 0
    data = load_json(COUNTER_FILE)
    if (
        not isinstance(data, int)
        or isinstance(data, bool)
        or data < 0
    ):
        raise ValueError("The counter must be a non-negative integer.")
    return data

def save_counter(counter):
    if (
        not isinstance(counter, int)
        or isinstance(counter, bool)
        or counter < 0
    ):
        raise ValueError("The counter must be a non-negative integer.")

    save_json(COUNTER_FILE, counter)


def generate_ticket_id(counter):
    new_counter = counter + 1
    ticket_id = f"T{new_counter}"
    save_counter(new_counter)
    return ticket_id, new_counter

def load_staff():
    if not STAFF_FILE.exists():
        save_staff(DEFAULT_STAFF.copy())
        return DEFAULT_STAFF.copy()

    staff = load_json(STAFF_FILE)

    if not isinstance(staff, list) or not all(
        isinstance(name, str) and name.strip()
        for name in staff
    ):
        raise ValueError("The staff file must contain a list of names.")

    return staff

def save_staff(staff):
    save_json(STAFF_FILE, staff)

def validate_counter(counter, tickets):
    highest_ticket_number = max(
        (
            int(ticket_id[1:])
            for ticket_id in tickets
            if ticket_id.startswith("T")
            and ticket_id[1:].isdigit()
        ),
        default=0,
    )

    if counter < highest_ticket_number:
        print(
            "\nWARNING: The ticket counter is lower than "
            "the highest saved ticket ID."
        )
        print(f"Counter value: {counter}")
        print(f"Highest ticket number: {highest_ticket_number}")

        while True:
            choice = input(
                "Enter 'f' to fix the counter or 'q' to quit: "
            ).strip().lower()

            if choice == "q":
                raise SystemExit("Application terminated.")

            if choice == "f":
                save_counter(highest_ticket_number)
                print(
                    f"Counter corrected to {highest_ticket_number}."
                )
                return highest_ticket_number

            print("Invalid choice. Enter 'f' or 'q'.")

    return counter


def load_application_data():
    ensure_data_files()
    tickets = load_tickets()
    counter = load_counter()
    staff = load_staff()
    counter = validate_counter(counter, tickets)
    return tickets, counter, staff