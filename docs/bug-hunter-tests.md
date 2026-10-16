# Bug-hunter tests

Two tests written by hunting for a failure rather than by describing a
requirement. Both live in the suite, both are named in a comment where they sit,
and both are recorded here in the brief's format: *initial state, input,
expected, actual, test name, change made*.

Evidence labels follow the project convention. **VERIFIED** means measured in
this environment; **OBSERVED** means read from source.

---

## BH-1 — a duplicated ticket ID made a ticket disappear silently

**Where:** `tests/test_storage.py::TestStorageRejectsBadData::test_duplicate_ticket_id_is_rejected`

### Initial state

The first version of the storage layer read the ticket file with a plain
`json.load`:

```python
def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
```

(OBSERVED — `git show 0a4f00f:campusflow/storage.py`.)

### Input

A `tickets.json` holding two records under the same key:

```json
{"T1": {"id": "T1", "title": "first",  ...},
 "T1": {"id": "T1", "title": "second", ...}}
```

### Expected

The file is not trustworthy — one of the two tickets is unreachable no matter
what the app does next — so the load should be refused and the user told.

### Actual

`json.load` does not treat a repeated key as an error. It builds a dictionary,
and the second assignment simply overwrites the first. **VERIFIED** — measured:

```
BH-1 json.load keeps: [('T1', {'id': 'T1', 'title': 'second'})]
BH-1 complained:      False
```

So the app loaded one ticket, reported no problem, and the "first" ticket was
gone. Nothing anywhere in the codebase could have noticed: the file is valid
JSON, the surviving record passes every field check, and the key matches the
stored `id`. The loss is silent and permanent, and it happens on a file a person
can edit by hand.

### Change made

Duplicate keys are now detected while the file is being decoded, before any
record is examined. `campusflow/jsonio.py` passes an `object_pairs_hook` to
`json.load`:

```python
def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise DataError(f"Duplicate key '{key}' in the JSON file. ...")
        seen[key] = value
    return seen
```

The hook is opt-in (`load_json(path, reject_duplicate_keys=True)`) because the
category file and the staff file do not need it; the ticket file does.

### Why refusing is the right answer, not merging

There is no honest way to merge two records that claim the same ID. Picking
either one discards a real ticket, and there is no field that says which is
newer. Refusing the load hands the decision to the person who can look at the
file, and — because the caller keeps its current in-memory tickets after a
`DataError` — the running app does not lose anything either.

---

## BH-2 — the resolution percentage on an empty dataset

**Where:** `tests/test_reports.py::TestEmptyReport::test_resolution_percentage_is_zero_not_a_crash`

### Initial state

The first version's `generate_report` had no percentage at all:

```python
return {
    "total": len(tickets),
    "by_status": dict(status_counts),
    "by_priority": dict(priority_counts),
}
```

(OBSERVED — `git show 0a4f00f:campusflow/reports.py`.)

So this is **not** a regression: there is no before-behaviour to record, because
the field did not exist. It is a guard test, written before the requirement was
implemented. Requirement D adds "resolution %" to the report, and the obvious
implementation is `resolved / total * 100`.

### Input

An empty ticket collection — `generate_report({})`.

### Expected

`0.0`, and a printed report that says so. An empty queue is *the normal state of
a fresh installation*, not an edge case: it is exactly what `main.py` holds on a
first run, before anyone has created a ticket. So this path is reached by every
new user on their first visit to the Reports screen.

### Actual (of the naive implementation)

**VERIFIED** — measured:

```
BH-2 naive percentage raises: ZeroDivisionError division by zero
```

`print_report` also returns early when the total is zero, so a percentage
computed anywhere after that early return would never even be displayed — the
crash would land at the point the report is *built*, taking the whole menu
option down with an unhandled exception rather than a friendly message.

### Change made

The percentage is computed behind an explicit guard, and the zero case is a
value rather than a branch:

```python
"resolution_percentage": (
    round(resolved / total * 100, 1) if total else 0.0
),
```

`print_report` keeps its original early return — `Total tickets: 0` followed by
empty breakdowns would be a worse screen than the sentence the first version
printed — and gains one line so the zero case still answers the percentage
question. Measured output for an empty collection:

```
No tickets yet.
Resolution: 0.0% (0 of 0 resolved)
```

Keeping the early return is deliberate: it is original behaviour, and the brief
requires the original behaviour to be preserved. What was missing was only the
percentage, so only the percentage was added.

### Note on `unresolved`

Writing this test surfaced a second decision. `unresolved` is the requirement's
"open + in_progress". The tempting implementation is `total - resolved`, which
gives the same number for the three statuses this app has — and would silently
become wrong the moment a fourth status existed. It is counted directly instead,
and `test_status_counts_add_up_to_the_total` pins the arithmetic both ways:
`sum(by_status.values()) == total` **and** `unresolved + resolved == total`.

---

## What these two have in common

Both bugs are invisible to a test that only exercises the happy path, and both
are reachable from the *shipped* project rather than from misuse:

- BH-1 needs a file a person edited, which the app's own "start fresh"
  documentation encourages them to do.
- BH-2 needs an empty dataset, which is the state the app starts in.

Neither would have been caught by the 41 tests the project began with.
