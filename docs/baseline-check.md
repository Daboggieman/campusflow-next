# Baseline check

What the project did **before** any CampusFlow Next changes, measured rather
than remembered. Everything here was run in this environment on 2026-10-16.

Baseline revision: `0a4f00f` (`mutable recall from initial repository
campusflow-adogah (for audit and improvement)`).

---

## 1. How the baseline was obtained

The original tree was extracted to a scratch directory outside the repository
and its tests were run there, so the measurement cannot have been contaminated
by anything added since. No branch, worktree or commit was created:

```bash
BASE=/tmp/cf-baseline
mkdir -p "$BASE"
for f in $(git ls-tree -r --name-only 0a4f00f | grep -E '\.py$'); do
  mkdir -p "$BASE/$(dirname "$f")"
  git show "0a4f00f:$f" > "$BASE/$f"
done
cd "$BASE" && python -m unittest discover -s tests -v
```

## 2. The baseline test run

**Command:** `python -m unittest discover -s tests -v`

**Result (VERIFIED — measured):**

```
Ran 41 tests in 0.020s

OK
```

| Module | Tests | Note |
|---|---:|---|
| `test_tickets.py` | 14 | |
| `test_workflow.py` | 13 | |
| `test_storage.py` | 6 | |
| `test_priority.py` | 4 | |
| `test_reports.py` | 4 | |
| **Total** | **41** | all passing |

Not one of the 41 was deleted or weakened. Every one still runs against the new
code; the four modules that grew (tickets, workflow, storage, reports) kept
their original tests unchanged and gained new ones beside them.

**Current:** `Ran 246 tests` — `OK`.

### The original tests are all still there

Two separate measurements, because they establish different things.

1. **All 41 original test names are present in the new tree.** Checked by
   parsing both versions with `ast` and comparing `Class.method` names:

   | Module | Original | Still present | Missing |
   |---|---:|---:|---|
   | `test_tickets.py` | 14 | 14 | — |
   | `test_workflow.py` | 13 | 13 | — |
   | `test_storage.py` | 6 | 6 | — |
   | `test_priority.py` | 4 | 4 | — |
   | `test_reports.py` | 4 | 4 | — |
   | **Total** | **41** | **41** | **none** |

   This check initially reported **40/41**:
   `TestStorageBrokenFile.test_save_then_load_builds_ticket_objects`, an empty
   save/load round trip, had not been carried across. It has been restored under
   its original class name so the count is honest rather than adjusted in the
   text.

2. **The original 41 tests, unmodified, pass against the rewritten package.**
   The baseline `tests/` directory was copied into the repository, run there so
   the imports resolved to the new `campusflow`, and then removed:

   ```
   Ran 41 tests in 0.016s

   OK
   ```

   This is the stronger of the two. A name can survive while its body is
   quietly weakened; this runs the original bodies against the original
   assertions.

## 3. Three inputs the baseline got wrong

The brief asked for three inputs. Five were measured, against the same
construction in both trees, because the first three all come from the same root
cause (a check that was missing rather than merely loose) and the last two
confirm which checks *were* already sound.

### The measurement

```python
Ticket(id="T1", title="network issue", category="network", urgency="medium",
       affected_users=5, priority="medium", status="open", assigned_to=None)
# ... with one field overridden per row
```

| Input | Baseline (`0a4f00f`) | CampusFlow Next |
|---|---|---|
| `affected_users=True` | **accepted**, stored `1` | `ValidationError: Affected users must be a whole number, not True/False.` |
| `affected_users=3.7` | **accepted**, stored `3` | `ValidationError: Affected users must be a whole number, not a decimal.` |
| `status="banana"` | **accepted**, stored `"banana"` | `ValidationError: 'banana' is not a valid status. Choose one of: open, in_progress, resolved.` |
| `affected_users="0"` | `ValueError: Affected users cannot be less than 1.` | `ValidationError: Affected users must be 1 or more.` |
| `category="billing"` | `ValueError: Choose one of: network, hardware, software, administrative, other.` | `ValidationError: 'billing' is not a valid category. ...` |

Both columns are **VERIFIED** by running the two trees side by side.

### Why the first three matter

**`affected_users=True` became 1.** `isinstance(True, int)` is true in Python, so
the value sailed through the integer check. `True` is not a number of people; it
is what a caller passes for "yes". A ticket that affected one person and a
ticket whose count was accidentally a boolean were indistinguishable afterwards.

**`affected_users=3.7` became 3.** The value was silently truncated. Worse, the
truncation moves the ticket *across a priority threshold*: 3.7 affected users
rounds down to 3, and `3+ users` is the medium-priority rule, so a count that
should have been rejected instead changed the ticket's priority.

**`status="banana"` was stored.** `Ticket.__post_init__` validated the category,
the urgency and the title, but never the status. A file could therefore contain
a ticket in a state the state machine has no moves for: it would not appear in
the Open Work Queue (not `open` or `in_progress`), would not count as resolved in
the reports, and `move_ticket` would refuse every transition out of it. The
ticket was reachable in memory and unreachable from every menu option.

### Why the last two were kept in the table

They show the baseline was not uniformly weak. `affected_users="0"` and an
unknown category were both refused, with messages that name the valid options.
Those messages are preserved nearly verbatim in the new code, which matters for
a person who has learned them.

## 4. What the audit found

The full list of defects found by reading the baseline source, each with where
it now lives and how it is covered. "Covered by" names a test that fails if the
fix is reverted.

### Silent data loss and silent corruption

| # | Defect in `0a4f00f` | Now | Covered by |
|---|---|---|---|
| 1 | `json.load` keeps the **last** of two identical keys, so a duplicated ticket ID lost a ticket with no error | duplicate keys rejected during decode | `test_duplicate_ticket_id_is_rejected` (BH-1) |
| 2 | `True` accepted as a user count | booleans refused before the integer branch | `test_check_affected_users_*` |
| 3 | `3.7` truncated to `3` | floats refused rather than truncated | `test_check_affected_users_rejects_decimal_text` |
| 4 | `status` never validated, so `"banana"` loaded | legal statuses enforced on construction and on load | `test_rejects_an_invalid_status` |
| 5 | stored `priority` never re-derived, so a hand-edited priority loaded as written | the priority the rules imply is recomputed and compared at load | `test_an_inconsistent_priority_is_rejected` |
| 6 | `save_json` opened the target for writing and truncated it in place — a crash mid-write left an unreadable file | written to a temp file in the same directory, then `os.replace`d | `test_saving_leaves_no_temporary_files_behind` |
| 7 | `load_tickets` validated record by record into one dictionary, so a failure part-way could leave a half-filled result | a fresh dictionary is returned only after **every** record validates | `test_a_partially_valid_file_does_not_replace_memory` |

### The data layer had a user interface

| # | Defect | Now | Covered by |
|---|---|---|---|
| 8 | `load_tickets` called `input()` and could `raise SystemExit` | raises `DataError`; the prompt lives in `main.py` | `test_a_failed_reload_does_not_erase_what_is_in_memory` |
| 9 | `validate_counter` called `input()` and could `raise SystemExit` | returns `(counter, warnings)`; `main.py` prints them | `test_reload_continues_id_generation_without_colliding` |

A storage module that reads the keyboard cannot be tested without a person
typing, and cannot be called by anything else. Every one of the tests above
became possible only after this was fixed.

### An ID could be burned

| # | Defect | Now | Covered by |
|---|---|---|---|
| 10 | `generate_ticket_id` wrote the counter **before** returning the ID, so a create that then failed consumed an ID for no ticket | `next_ticket_id` is pure; the counter is written only after the ticket is built | `test_next_ticket_id_does_not_write_anything` |

### Features the brief adds, absent from the baseline

| # | Missing | Now |
|---|---|---|
| 11 | no `notes` field | `campusflow/notes.py`, `N001`-style IDs per ticket |
| 12 | no search | `campusflow/search.py`, read-only, no printing |
| 13 | no resolution percentage, no unresolved/resolved counts, no category counts | `campusflow/reports.py` |
| 14 | categories hard-coded in `tickets.py` | `campusflow/categories.py`, active/retired, editable data |
| 15 | no understanding check | `campusflow/understanding_check.py` |

`DataError` is deliberately **not** a `ValueError` subclass. The baseline's
`except (json.JSONDecodeError, TypeError, ValueError, KeyError)` would have
swallowed a data-integrity failure and treated it as a bad keystroke. Keeping
the two types unrelated means a broad `except ValueError` cannot confuse them.

## 5. The shipped data still loads

The three tickets in `data_folder/tickets.json` were written by the baseline,
in the baseline's format: no `notes` key, and `assigned_to` recorded as `false`
for "nobody".

**VERIFIED — measured:**

```
loaded tickets: ['T1', 'T2', 'T3']
  T1: 'network in facility' critical open assigned=None  notes=[]
  T2: 'pebbles'             high     open assigned=None  notes=[]
  T3: 'unknown'             critical open assigned='Mr. Izzy' notes=[]
counter: 3   warnings: []
next id preview: ('T4', 4)
```

Requirement E's "do not discard old working tickets" is therefore satisfied
against real data, not only against fixtures: `false` is read as unassigned, the
missing `notes` key becomes an empty list, all three stored priorities agree
with the priority rules, and the next ID continues from `T4` rather than
restarting.
