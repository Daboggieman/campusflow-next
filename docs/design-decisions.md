# campusflow: design decisions

engieneer 1: Adakole Raph'el Ogah
previous-engieneer 2: Deborah Okpanya
engieneer 2: Deborah John

## What this is

campusflow is a text-only python cmd line app. It records support problems (Wi-Fi outages, faulty laptops, broken development environments, inaccessible platforms), works out the problems priority, assigns responsibility of reported issue, and tracks progress.

## 1. Decision: simple Inputs --> Process --> Outputs --> Failures / success table**


## 2 Ticket fields

Each ticket stores: `id`, `title`, `category`, `urgency`, `affected_users`, `priority`, `status`, `assigned_to`.

IDs are unique and generated automatically (T1, T2, T3 ...). Categories are Network, Hardware, Software, Other. Urgencies are low, medium, high. input validation were included for `title`, `affected_users` and the rest, invalid input shows an error.

> tickets are held in a dataclass.**

> Validation: inside the dataclass, so that a bad ticket can never be created.** Following the F1 decision, the field checks live in small helper functions. The dataclass calls them, and so does the menu when it asks for each field.

>Unique IDs: a `latest_ticket_id` value holding the highest ID so far.** To make a new ticket, read the value (for example T029), add 1 to get T030, then update the value to T030. An ID is never reused, even if a ticket is deleted or modified. The value is stored in its own `counter.json` file (see F7) so it survives restarts.

## 3 Priority calculation

Rules are checked in this order, and the first match wins:

1. High urgency and 10 or more affected users = critical
2. High urgency or 10 or more affected users = high
3. Medium urgency or 3 or more affected users = medium
4. Everything else: low

> written as an if / elif chain, top to bottom

> Lives in a separate function in its own file (`priority.py`), so it is easy to test alone.

## 4 The applications main features

### Create

Ask for one field at a time and re-ask only that field until it is valid, with input validation on every input. Then calculate priority, generate the ID and store the ticket in data/.

### List / View

Two steps. First a short list (ID, title, priority, status). Then the user enters an ID to see full details.

### Assign

The user picks a staff member from a saved staff list. Unknown ticket IDs are rejected. Tickets are kept in memory in a dictionary stored by id for easy search. A resolved ticket cannot be assigned again until it is reopened. The staff list is read from `data_folder/staff.json/`

### Workflow

An `in_progress` ticket cannot go back to `open`. An unassigned ticket cannot move to `in_progress`. A resolved ticket can only be modified after it is reopened.

### Work queue

Shows tickets that are "open" or "in_progress".

### Reports

the report.py file has two functions one works out the total tickets, counts them by status, counts them by priority and returns them, and one prints them plain. if there are no tickets in data_folder it returns "no tickets yet" message.

### Persistence

- saves are madeafter every change
- bad JSON, or a ticket that fails the dataclass checks shows the error and ask whether to quit or start afresh. starting fresh first copies the broken file to a backup name
- for example the counter is missing, or lower than the highest ticket it show a warning and ask the user to fix it or quit
- on a first run with no files, start fresh with the counter at zero, so the first ticket is T1

## 5 file layout and tests

**File layout:** the owner's own tree, plus three additions (`priority.py`, `test_priority.py`, `test_reports.py`) and the runtime `data_/` folder.

```
campusflow/
├── README.md
├── .gitignore
├── main.py
├── campusflow/
│   ├── __init__.py
│   ├── tickets.py
│   ├── priority.py
│   ├── workflow.py
│   ├── storage.py
│   └── reports.py
├── tests/
│   ├── test_tickets.py
│   ├── test_priority.py
│   ├── test_workflow.py
│   ├── test_storage.py
│   └── test_reports.py
├── data/
│   ├── tickets.json
│   ├── counter.json
│   └── staff.json
└── docs/(mutable- log file name can change or increase due to switching users and collaborators)
    ├── ai-learning-log.md
    └── design-decisions.md(do not delete, only add to this, leave the old desicion docs as they were add new finding/improbemnts without mutatuing the old one)
```