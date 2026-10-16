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
---

# CampusFlow Next — decisions added 2026-10-16

Nothing above this line has been changed. The original decisions, including the
file-layout block and its own instruction not to delete anything, are left
exactly as they were. What follows is added.

## 6 Validation lives in one place, and the two failures are different types

Every field is checked by a function in `campusflow/tickets.py`, and every check
that spans records lives in `campusflow/validation.py`. The CLI, the storage
layer and the note layer all call the same functions, so a rule cannot be
enforced in one path and forgotten in another.

Two exception types, and the distinction is the point:

- `ValidationError(ValueError)` — the user typed something the rules refuse.
  Recoverable, so the CLI prints the message and re-prompts.
- `DataError(Exception)` — stored data cannot be trusted. The load is abandoned.

`ValidationError` subclasses `ValueError` for backward compatibility: the 41
tests the project began with all say `assertRaises(ValueError)`, and none of them
was rewritten. `DataError` is deliberately **not** a `ValueError`, because the
original storage code caught `ValueError` broadly and treated a corrupt file as a
typo. Keeping the two unrelated means that handler — and any `except ValueError`
written by habit — cannot swallow a data-integrity failure.

## 7 Validate before mutate

A rejected action must leave the collection byte-for-byte identical. So every
function that writes computes all of its derived values first and performs a
single write last. `notes.add_note` is the clearest case: it checks the ticket's
status, then the author, then the message, and only then derives the note ID and
appends. Nothing is written between the first check and the last.

The visible consequence is that **a refused note does not consume a note ID**.

## 8 A load is all-or-nothing

`load_tickets` builds a completely fresh dictionary and returns it only after
every record has validated. A file whose last record is broken therefore leaves
the caller's existing tickets untouched rather than half-overwritten.

This replaces the original `load_tickets`, which validated record by record into
one dictionary and could return a partial result — or prompt the user and
`raise SystemExit` from inside the storage module.

## 9 Priority consistency is enforced on load, not on construction

Requirement E asks that a stored priority which disagrees with the priority rules
be caught. The obvious home is `Ticket.__post_init__`, beside every other check.
It is not there.

The reason is measurable: roughly ten existing test fixtures deliberately pair
`urgency="medium", affected_users=5` with a pinned priority of `high`, `critical`
or `low`, because those tests are about **work-queue ordering**, not about
priority derivation. Enforcing consistency at construction would fail all of
them — and rewriting them would be weakening tests to fit new code.

So the check lives in `validation.validate_ticket_record`, where it runs on load
only. The requirement's actual guarantee is kept: a hand-edited priority cannot
be loaded silently. All three tickets in the shipped `data_folder` were measured
against the rules and are consistent, so nothing legitimate is rejected.

## 10 Ticket IDs stay unpadded; note IDs are padded

`T1`, `T2`, `T3` — not `T001`. Existing files and existing user habits are left
alone, and both spellings load. This was the owner's decision, and it is the
smaller change.

Note IDs are the opposite: `N001`, `N002`, always three digits. They are new in
this version, so there is no old spelling to respect, and three digits sorts
correctly as text for the realistic range.

Two deliberately different conventions. Both patterns are named at the top of
`tickets.py` (`TICKET_ID_PATTERN`, `NOTE_ID_PATTERN`) so the difference is
visible rather than accidental.

## 11 A note ID is derived from the notes present, not counted in a file

`next_note_id` takes the highest note ID on *that ticket* and adds one. There is
no `notes_counter.json`.

A separate counter would be a second source of truth that can drift out of step
with the ticket file — and it is the exact shape of the original
`counter.json`/`tickets.json` divergence, which needed a whole reconciliation
step (`validate_counter`) to repair on load. Deriving it means notes N001 and
N003 make the next one N004 and never N002 again, with nothing to reconcile.

## 12 The category list is editable data, with an active/retired split

The five starting categories are no longer a constant in `tickets.py`. They are
data in `data_folder/categories.json`, with two sets:

- **active** — offered when creating a ticket
- **retired** — still valid on tickets that already use it, never offered again

Retiring therefore cannot orphan an existing ticket, which is what Requirement E
means by "do not discard old working tickets". `check_category` validates a
stored record against active *plus* retired; `validate_new_category` validates
new input against active only, and the two are different functions so the
distinction cannot be lost.

The last active category cannot be retired: every ticket needs a category, so an
empty active list would make the create screen impossible to complete.

**Rejected alternative:** a per-ticket "edit this ticket's category" action. The
owner asked for the list to be editable *data* managed from a menu, not a way to
rewrite individual tickets — and editing one ticket's category would not answer
the question "what categories does this campus use".

## 13 Search is read-only and does not print

`campusflow/search.py` contains no writes and no `print`. The CLI calls it freely
knowing a search cannot corrupt anything, and the tests compare returned lists
instead of capturing output. `_print_search_results` in `main.py` owns the
display.

Filters are **AND**: every supplied filter must match. Blank means "do not filter
on this field", decided by `strip()` in one shared helper — **not** by
truthiness, because `bool("   ")` is `True` and a space-then-Enter would have
become a real filter that matched nothing.

**Rejected alternative:** fuzzy or spelling-corrected matching. `wifi` does not
find `Wi-Fi`, and that is deliberate — the brief rules out promising spelling
correction, and a search that quietly guesses is worse than one that honestly
misses. Comparison uses `casefold()` rather than `lower()` so that `STRASSE`
does find a title stored as `Straße`.

## 14 The Open Work Queue is unchanged; the priority view is separate

`get_work_queue` still returns `open` plus `in_progress`, sorted by priority rank
then numeric ticket number. The brief requires the original queue to be left
alone and offers the priority-ordered view as something additional; that is the
separate menu entry "search tickets by priority", which sorts *search results*
by priority and ticket ID. It is a view over search output and does not touch the
queue.

## 15 Reports: 0% on an empty dataset, nothing counted twice

`generate_report` returns `total`, `by_status`, `by_priority`, `by_category`,
`unresolved`, `resolved` and `resolution_percentage`.

- `resolution_percentage` is `round(resolved / total * 100, 1) if total else 0.0`.
  An empty dataset is the **normal** state of a fresh install — it is what the
  Reports screen shows a brand-new user — so this path had to answer rather than
  raise. Written up as bug-hunter test BH-2.
- `unresolved` is counted from the statuses directly, not as `total - resolved`.
  Both give the same number for these three statuses, which is exactly why the
  subtraction is a trap: it would silently become wrong the moment a fourth
  status existed.
- A reopened ticket counts by its **current** status. Counting follows the
  record, not its history.

The tests assert both `sum(by_status) == total` and
`unresolved + resolved == total`.

## 16 The storage layer no longer reads the keyboard

The original `load_tickets` and `validate_counter` called `input()` and could
`raise SystemExit`. A storage function that prompts cannot be tested without a
person typing, and cannot be called by anything else.

They now raise `DataError` or return their warnings; `main.py` prints them and
offers quit-or-start-fresh. Every storage test became possible only after this
change, which is why it was made before the features that needed it.

## 17 Saves are atomic

`save_json` creates a temporary file in the **same directory** as the target
(same filesystem, so the rename is a rename and not a copy), writes and closes
it, then calls `os.replace`. The original opened the target with `"w"`, which
truncates it immediately, so a crash during the write left a truncated file — and
a truncated file triggers "start fresh", which is data loss caused by a crash
that had nothing to do with the data.

If the write raises, the temporary file is removed so a failed save does not
litter the data folder.

## 18 The understanding check keeps the bank and the scoring apart

The question bank is data — a list of dictionaries with a `prompt`, four
`options`, an `answer` and a `reference`. The scoring functions are logic and
hold no copy of the answers; they read the `answer` field from the bank. A test
asserts the bank contains no callables at all, so it cannot disagree with the
scoring.

Explanations for at least two answers are stored **verbatim** and never graded.
Auto-grading prose by keyword matching would reward writing the expected words
rather than understanding, and would mark a correct explanation phrased
differently as wrong.

## 19 Rejected: quietly repairing bad input

Every place where the original accepted something it should not have, the new
code refuses rather than repairs. Three cases, all measured in
[baseline-check.md](baseline-check.md):

| Input | Original | Now |
|---|---|---|
| `affected_users=True` | stored as `1` | refused — `isinstance(True, int)` is true, so booleans need their own check |
| `affected_users=3.7` | truncated to `3` | refused — the truncation could move the ticket across a priority threshold |
| `status="banana"` | stored as written | refused — an unhandled status makes a ticket reachable in memory and unreachable from every menu |

Rounding, coercing and guessing all produce a program that appears to work while
the data is wrong. Refusing produces a message the user can act on.

## 20 What was not changed

For the record, because each of these looks like an obvious fix:

- **Display titles are stored lowercase**, and `check_title` uses `lower()` while
  comparison uses `casefold()`. Search casefolds both sides, so the behaviour is
  correct as it stands; changing storage would rewrite the titles of tickets that
  already exist for no behavioural gain.
- **The staff list and the note author are free text when adding a note.**
  Assignment picks from `staff.json`, but a note records whoever wrote it, who
  need not be on that list.
- **`data_folder/` is runtime state and is not deleted or migrated.** The three
  tickets that were there before still load, in the same format.
