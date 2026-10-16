# campusflow

## What this is

campusflow is a text-only python cmd line app. It records support problems (Wi-Fi outages, faulty laptops, broken development environments, inaccessible platforms), works out the problems priority, assigns responsibility of reported issue, and tracks progress.

**CampusFlow Next** is the same program, extended. Every original feature still
works, and the 41 tests the project began with still pass unchanged. What was
added: follow-up notes on a ticket, a read-only search, a fuller report, an
editable category list, and an engineering understanding check. What changed
underneath: validation is centralised, a rejected action provably changes
nothing, and a damaged data file is refused instead of half-loaded.

## 1. Decision: simple Inputs --> Process --> Outputs --> Failures / success table**


## 2 Ticket fields

Each ticket stores: `id`, `title`, `category`, `urgency`, `affected_users`, `priority`, `status`, `assigned_to`, `notes`.

IDs are unique and generated automatically (T1, T2, T3 ...). Categories come from an editable list that starts as network, hardware, software, administrative, other. Urgencies are low, medium, high. input validation were included for `title`, `affected_users` and the rest, invalid input shows an error.

> tickets are held in a dataclass.**

> Validation: inside the dataclass, so that a bad ticket can never be created.** Following the F1 decision, the field checks live in small helper functions. The dataclass calls them, and so does the menu when it asks for each field.

>Unique IDs: a `latest_ticket_id` value holding the highest ID so far.** To make a new ticket, read the value (for example T029), add 1 to get T030, then update the value to T030. An ID is never reused, even if a ticket is deleted or modified. The value is stored in its own `counter.json` file (see F7) so it survives restarts.

>Ticket IDs stay unpadded.** T1, T2, T3 — not T001. Existing files and existing
>user habits are left alone, so `T1` and `T001` can both appear in one file and
>both load. **Note IDs are the opposite**: `N001`, `N002`, always three digits,
>because they are new in this version and there is no old spelling to respect.
>The two conventions are deliberately different and the code says so where it
>matters (`TICKET_ID_PATTERN` and `NOTE_ID_PATTERN` in `tickets.py`).

## 3 Priority calculation

Rules are checked in this order, and the first match wins:

1. High urgency and 10 or more affected users = critical
2. High urgency or 10 or more affected users = high
3. Medium urgency or 3 or more affected users = medium
4. Everything else: low

> written as an if / elif chain, top to bottom

> Lives in a separate function in its own file (`priority.py`), so it is easy to test alone.

> The thresholds have names.** `CRITICAL_USER_THRESHOLD` is 10 and
>`AFFECTED_USER_THRESHOLD` is 3, so a policy change is one edit rather than a
>search for loose numbers. The output for every input is unchanged from the
>first version.

> A stored priority must agree with these rules.** When a ticket file is loaded,
>the priority is recalculated from `urgency` and `affected_users` and compared
>against what the file says. A disagreement refuses the whole load. This is what
>stops a hand-edited priority being silently wrong — but it is enforced **on
>load only**, never when a ticket object is built, so the existing tests that
>pair a fixed priority with arbitrary urgency still work. See
>`validate_ticket_record` in `validation.py`.

## 4 The applications main features

### Create

Ask for one field at a time and re-ask only that field until it is valid, with input validation on every input. Then calculate priority, generate the ID and store the ticket in data/.

> The ID is previewed but not committed.** If the ticket cannot be built, the
>counter is not written and no ID is burned. `storage.next_ticket_id` is the
>pure preview form; `storage.generate_ticket_id` is the one that writes.

### List / View

Two steps. First a short list (ID, title, priority, status). Then the user enters an ID to see full details.

### Assign

The user picks a staff member from a saved staff list. Unknown ticket IDs are rejected. Tickets are kept in memory in a dictionary stored by id for easy search. A resolved ticket cannot be assigned again until it is reopened. The staff list is read from `data_folder/staff.json/`

### Workflow

An `in_progress` ticket cannot go back to `open`. An unassigned ticket cannot move to `in_progress`. A resolved ticket can only be modified after it is reopened.

> The whole rule is one pure predicate.** `workflow.can_transition(current,
>new)` answers the question without touching a ticket, and `move_ticket` asks
>it. Pinning the predicate pins the rule, which is why
>`tests/test_workflow.py` tests the full 3×3 matrix rather than a few cases.

### Work queue

Shows tickets that are "open" or "in_progress".

> **Unchanged from the first version, and deliberately so.** Still `open` plus
>`in_progress`, still sorted by priority rank and then by numeric ticket number.
>The brief asks for the original queue to be left alone and offers the
>priority-ordered view as something *separate* — that is the extra menu entry
>"search tickets by priority", which sorts the **search results** and does not
>touch the queue.

### Notes (new)

"A follow-up note" and "view ticket notes" are two menu entries.

- A note is `{note_id, author, message}`. Note IDs are per-ticket, starting at
  `N001` and counting up.
- Notes can only be added to an `open` or `in_progress` ticket. A resolved
  ticket has to be reopened first.
- The author cannot be blank after trimming. The message must be 5 to 300
  characters after trimming.
- **A rejected note does not consume a note ID.** The ID is derived from the
  notes actually present and is only computed once everything else has passed,
  so this sequence works: add N001, add N002, resolve, attempt N003 (refused),
  reopen, add N003 — not N004.
- Notes are read back in ID order, and they survive resolve/reopen and a
  save/reload.

### Search (new)

A read-only screen. Nothing in `search.py` writes and nothing in it prints.

- The title search is a **case-insensitive substring** match. `wi-fi` finds
  `Wi-Fi down in the library`. It is not fuzzy: `wifi` does **not** find
  `Wi-Fi`, because the brief rules out promising spelling correction.
- Category, status and priority are optional filters. **Every supplied filter
  must match — they are AND, not OR.** Blank means "do not filter on this
  field", so pressing Enter at every prompt shows everything.
- An unrecognised filter option re-prompts instead of quietly matching nothing.
- Each result shows ID, title, category, priority, status and who it is assigned
  to (`unassigned` when nobody).
- Search never modifies a record — `TestSearchIsReadOnly` asserts the whole
  collection is byte-for-byte identical after a search.

### Reports

the report.py file has two functions one works out the total tickets, counts them by status, counts them by priority and returns them, and one prints them plain. if there are no tickets in data_folder it returns "no tickets yet" message.

> Now also counts by category, and reports unresolved (open + in_progress),
>resolved, and resolution % (resolved / total × 100, rounded to one decimal).

> An empty dataset reports 0.0%, not a crash.** `resolved / total` is a
>`ZeroDivisionError` when there is nothing to report, and an empty dataset is
>the *normal* state of a fresh install — it is what the Reports screen shows a
>brand-new user. Written up as bug-hunter test BH-2 in
>[docs/bug-hunter-tests.md](docs/bug-hunter-tests.md).

> A reopened ticket counts by its CURRENT status, and nothing is double-counted.**
>`unresolved` is counted from the statuses directly rather than as
>`total - resolved`, and the tests assert both
>`sum(by_status) == total` and `unresolved + resolved == total`.

### Categories (new)

The allowed category list is **application data**, not a constant in the code.
"Manage categories" adds a category or retires one, and the change is written to
`data_folder/categories.json`.

There are two sets: **active** (offered for new tickets) and **retired**
(still valid on tickets that already use it). Retiring a category therefore
cannot orphan an existing ticket — it stops being *chosen* for new work while
everything already filed under it keeps loading and displaying. The last active
category cannot be retired, because a ticket needs one.

### Engineering understanding check (new)

Six multiple-choice questions about how this program actually behaves, one point
each, 0–6. The question bank is **data** and the scoring is **logic**; the bank
contains no copy of the answers and no callables, so the two cannot disagree.
An answer that is not A, B, C or D is rejected and re-asked. The check then asks
for a short written explanation of at least two answers and stores them
**verbatim** — explanations are never graded by keyword matching. Sessions are
appended to `docs/understanding-notes.md`.

### Persistence

- saves are madeafter every change
- bad JSON, or a ticket that fails the dataclass checks shows the error and ask whether to quit or start afresh. starting fresh first copies the broken file to a backup name
- for example the counter is missing, or lower than the highest ticket it show a warning and ask the user to fix it or quit
- on a first run with no files, start fresh with the counter at zero, so the first ticket is T1

> Now strict, and all-or-nothing.** A load either produces a complete, valid
>collection or raises `DataError` and changes nothing. The caller's in-memory
>tickets survive a failed reload untouched, and the message offers
>quit-or-start-fresh. The original loader validated record by record into one
>dictionary and could therefore leave a half-filled result behind.

> Data-layer functions no longer read the keyboard.** The original
>`load_tickets` and `validate_counter` called `input()` and could `raise
>SystemExit` from inside the storage module, which made them untestable. They
>now raise, and `main.py` does the talking.

> Saves are atomic.** Written to a temporary file in the same directory, then
>`os.replace`d over the target. A crash mid-save cannot leave a truncated
>`tickets.json`, which would have triggered "start fresh" and lost data for a
>reason that had nothing to do with the data.

> Two error types, and they are deliberately unrelated.** `ValidationError` is a
>`ValueError`, so every original `assertRaises(ValueError)` test still passes and
>a bad keystroke is recoverable. `DataError` is **not** a `ValueError`, so a
>broad `except ValueError` cannot mistake "the file is untrustworthy" for "the
>user typed something odd".

---

## 5 The data file format

Everything lives in `data_folder/`. Four files.

### `tickets.json` — unchanged envelope

A single JSON object keyed by ticket ID. The envelope is the same as the first
version, so a file written by either version loads in the other:

```json
{
    "T1": {
        "id": "T1",
        "title": "network in facility",
        "category": "network",
        "urgency": "high",
        "affected_users": 20,
        "priority": "critical",
        "status": "open",
        "assigned_to": null,
        "notes": [
            {
                "note_id": "N001",
                "author": "Mr. Izzy",
                "message": "Router reboot attempted; switch ports checked next"
            }
        ]
    }
}
```

Notes on the format:

- **`notes` is written out but not required on the way in.** A file saved before
  CampusFlow Next has no `notes` key; it loads, and every such ticket simply
  starts with no notes.
- **`assigned_to` is `null` for unassigned**, but the original wrote `false` for
  the same thing. Both are accepted on load, and the shipped `data_folder`
  really does contain `false` — so the backward-compatibility path is exercised
  by the project's own data, not only by fixtures.
- Titles are stored trimmed and lowercase. Categories, urgencies, statuses and
  priorities are stored in their canonical lowercase spelling.
- `notes` is the only optional key. Anything else unexpected refuses the load,
  which is what makes a misspelled field visible instead of silently ignored.

### `counter.json`

A bare integer: the highest ticket number issued so far. On load it is compared
against the highest ID actually in `tickets.json`. If the counter is lower, it is
corrected upward and a warning is shown, so the next generated ID can never
collide with one already in the file.

### `staff.json`

A JSON list of staff display names, seeded with the original six on a first run.

### `categories.json`

```json
{
    "active": ["network", "hardware", "software", "administrative", "other"],
    "retired": []
}
```

A plain JSON list is also accepted in place of the envelope, so a hand-written
file does not have to know about it. Names are stored trimmed and casefolded,
and a category cannot be both active and retired at once. If the file is
missing it is seeded with the five defaults.

### What makes a file unusable

Any one of these refuses the entire load and leaves the running app's tickets
untouched:

- the top level is not a JSON object
- the same ticket key appears twice (checked while decoding — `json.load` would
  otherwise keep the last one silently; see BH-1)
- a required field is missing, or an unexpected field is present
- any field fails its own check (blank title, unknown category or urgency or
  status or priority, a non-positive or non-integer user count)
- the record's `id` disagrees with the key it is filed under
- the stored `priority` is not the one the priority rules imply
- a note is missing a key, has an extra key, has a blank author, has a message
  outside 5–300 characters, or repeats a note ID within the same ticket

## 6 file layout and tests

**File layout:** the owner's own tree, plus three additions (`priority.py`, `test_priority.py`, `test_reports.py`) and the runtime `data_/` folder.

```
campusflow/
├── README.md
├── .gitignore
├── main.py
├── campusflow/
│   ├── __init__.py
│   ├── errors.py            # ValidationError (recoverable) / DataError (not)
│   ├── jsonio.py            # safe JSON: duplicate keys, atomic saves, backups
│   ├── tickets.py           # the record and its field checks
│   ├── priority.py          # the priority rules
│   ├── workflow.py          # status moves, assignment, the work queue
│   ├── storage.py           # loading, saving, ID continuity
│   ├── validation.py        # the checks that span records, incl. load
│   ├── notes.py             # follow-up notes, validate-before-mutate
│   ├── search.py            # read-only search and filtering
│   ├── reports.py           # the report numbers and their display
│   ├── categories.py        # the editable category list
│   └── understanding_check.py  # the question bank and its scoring
├── tests/
│   ├── support.py           # shared fixtures (not collected by discovery)
│   ├── test_tickets.py
│   ├── test_priority.py
│   ├── test_workflow.py
│   ├── test_storage.py
│   ├── test_reports.py
│   ├── test_validation.py
│   ├── test_notes.py
│   ├── test_categories.py
│   ├── test_search.py
│   ├── test_understanding.py
│   └── test_cli.py
├── data_folder/             # created at runtime if missing
│   ├── tickets.json
│   ├── counter.json
│   ├── staff.json
│   └── categories.json
└── docs/
    ├── ai-learning-log.md              # index of the two logs below
    ├── ai-learning-log(Engieneer-1).md
    ├── ai-learning-log(Engieneer-2).md
    ├── baseline-check.md               # the 41-test baseline, measured
    ├── bug-hunter-tests.md             # BH-1 and BH-2
    ├── design-decisions.md             # do not delete, only add
    └── pseudocode.md
```

### Fresh clone: how to run it

No dependencies and no installation. Python 3 only, standard library only.

```bash
git clone <repository-url>
cd campusflow-next

# run the tests — the brief's command
python -m unittest discover -s tests -v          # expect: 246 tests, OK

# run the app
python main.py
```

On Windows the `py` launcher works the same way:

```powershell
py -m unittest discover -s tests -v
py main.py
```

`unittest discover -s tests` adds `tests/` to the import path, which is how the
test modules find `support.py`. Running the suite from a different directory
gives import errors that look like missing modules.

There are no external packages, no database, no web API and no network access at
any point. The only runtime state is the `data_folder/` directory, which is
created on the first run.

### The test suite

The brief asks for at least 14 meaningful `unittest` tests for the integrated
application, at least 5 authored by each engineer, plus 2 bug-hunter tests, all
runnable in a fresh clone with `python -m unittest discover -s tests -v`.
Delivered: **246 tests, `unittest` only**, measured per module:

| Owner | Modules | Tests |
|---|---|---:|
| Engineer 1 — ticket safety and storage | `test_tickets` 39, `test_validation` 21, `test_notes` 26, `test_storage` 29, `test_workflow` 19, `test_categories` 22 | 156 |
| Engineer 2 — search, reporting and CLI | `test_search` 21, `test_reports` 13, `test_cli` 32, `test_understanding` 20 | 86 |
| pre-existing, unchanged | `test_priority` | 4 |
| **total** | | **246** |

Two of them are bug-hunter tests rather than requirement tests —
[BH-1](docs/bug-hunter-tests.md) (a duplicated ticket key made a ticket vanish
silently) and [BH-2](docs/bug-hunter-tests.md) (the resolution percentage on an
empty dataset).

Requirement-to-test mapping, so a reviewer can check coverage rather than count
tests:

| Requirement | Owner | Test module | Representative tests |
|---|---|---|---|
| A — centralised validation; a rejected action changes nothing | Engineer 1 | `test_tickets`, `test_validation`, `test_cli` | `test_check_affected_users_rejects_decimal_text`, `test_rejects_a_missing_field`, `test_an_unassigned_ticket_cannot_start_work` |
| B — follow-up notes | Engineer 1 / 2 | `test_notes`, `test_cli` | `test_adds_a_note_to_an_open_ticket`, `test_a_short_note_is_refused_and_no_id_is_used`, `test_notes_are_preserved_through_resolve_and_reopen` |
| C — read-only search with AND filters | Engineer 2 | `test_search`, `test_cli` | `test_every_supplied_filter_must_match`, `test_filters_are_and_not_or`, `test_searching_does_not_change_any_ticket` |
| D — reports and the separate priority view | Engineer 2 | `test_reports`, `test_cli` | `test_a_reopened_ticket_counts_as_open`, `test_status_counts_add_up_to_the_total`, `test_puts_critical_first_then_the_rest_by_priority` |
| E — extended file format; a bad load changes nothing | Engineer 1 | `test_storage`, `test_validation`, `test_categories` | `test_notes_survive_a_save_and_load`, `test_the_next_note_id_survives_a_reload`, `test_a_partially_valid_file_does_not_replace_memory` |
| Understanding check (bank separate from scoring, no keyword grading) | Engineer 2 | `test_understanding` | `test_the_bank_contains_no_scoring_logic`, `test_explanations_are_recorded_verbatim_and_never_graded` |
| The original Open Work Queue, unchanged | Engineer 1 | `test_workflow` | `test_includes_open_and_in_progress_only`, `test_sorts_by_priority_rank` |

The 41 tests the project started with are all still present, by name, and were
additionally run **unmodified against the rewritten package** — all 41 pass.
Both measurements are in [docs/baseline-check.md](docs/baseline-check.md), along
with five inputs the original code got wrong.
