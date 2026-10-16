# AI learning log — Engineer 1 (Ticket Safety and Storage)

Three cycles, recorded in the brief's format: **concept gap → the exact question
asked → what the AI guidance said → a small experiment on unrelated ground →
independent verification against the real code → decision.**

The AI was used to explain a concept, then every claim was checked by running
something. Where the guidance and the measurement disagreed, the measurement
won; two of those disagreements are in the team section at the end.

Areas owned in this sprint: `tickets.py`, `validation.py`, `notes.py`,
`storage.py`, `jsonio.py`, `workflow.py`, `categories.py`.

---

## Cycle 1 — "a file with the same key twice should have raised"

### Concept gap

I could not explain why the original app lost a ticket when `tickets.json`
contained the same ticket ID twice. My assumption was that duplicate keys make a
JSON document malformed, so the parser should refuse it.

### Question asked

> Does `json.load` raise or warn when a JSON object contains the same key twice?
> If it does not, is there a way to see the duplicate before it is lost?

### Guidance given

`json.load` does not treat a repeated key as an error. It hands each pair to
`dict`, and `dict` keeps the last. The document is not malformed — the JSON
specification permits repeated names and leaves the behaviour to the
implementation, and Python's implementation is "last one wins". The way to see
the pairs before they collapse is the `object_pairs_hook` argument, which is
called with the complete list of `(key, value)` pairs in file order.

### Small experiment on unrelated ground

If `object_pairs_hook` is "called with the pairs of an object", what happens with
a JSON **array**, which has no keys? I predicted it would be called with
`(index, value)` pairs.

```python
calls = []
json.loads('[1, 2, 3]', object_pairs_hook=lambda pairs: calls.append(pairs) or dict(pairs))
print(calls)
```

Measured: **`[]`** — the hook is never called for an array.

So the hook is precisely "the pairs of an object", not "the pairs of anything".
That is what I needed to know, because it means adding the hook cannot change
how any array in the file is read.

### Independent verification

Two measurements, not one.

1. The duplicate-key behaviour itself, in the interpreter:

   ```
   BH-1 json.loads kept: [('T1', {'id': 'T1', 'title': 'second'})]
   BH-1 complained:      False
   ```

   Confirmed: no error, first record gone.

2. The fix, through the real loader — `tests/test_storage.py` writes the
   two-record file and asserts `DataError` with "Duplicate key" in the message.
   Passing.

### Decision

`campusflow/jsonio.py` gained `_reject_duplicate_keys` and `load_json` grew an
opt-in `reject_duplicate_keys=True` flag. Opt-in rather than always-on because
`staff.json` and `categories.json` do not need it and I did not want to change
their loading behaviour for no reason. Recorded as bug-hunter test **BH-1** in
[bug-hunter-tests.md](bug-hunter-tests.md).

**Evidence: VERIFIED.**

---

## Cycle 2 — "adding a new exception type would break 41 tests"

### Concept gap

Requirement A needs precise failures: "the user typed something bad" is
recoverable, "the stored file cannot be trusted" is not. I wanted two exception
types. My worry was that the project's existing tests all say
`assertRaises(ValueError)`, and the brief's first rule is that no original
feature may be lost — so a new exception type looked like it would force me to
rewrite 41 tests, which is exactly the "silently remove functionality" move I was
told not to make.

### Question asked

> If I introduce `ValidationError` for the new checks, will the existing tests
> that expect `ValueError` still pass? And what is the difference between
> `except ValueError` and `assertRaises(ValueError)` when the raised type is a
> subclass?

### Guidance given

`assertRaises(ValueError)` passes for any subclass of `ValueError`, because
`unittest` uses `isinstance` on the caught exception. So `ValidationError` can
subclass `ValueError` and every existing test keeps passing, while new code
catches the narrower type and cannot accidentally catch an unrelated `ValueError`
raised by, say, `int()`.

The second half of the guidance was the useful part: the same `isinstance`
behaviour means a *broad* `except ValueError` in the original storage code would
have swallowed a data-integrity failure. So the data error must **not** be a
`ValueError`, or the two failure modes become indistinguishable.

### Small experiment on unrelated ground

Does `assertRaises` behave the same when the mismatch goes the *other* way — a
non-subclass raised inside the block? I expected a clean test failure.

```
ValidationError is a ValueError: True
DataError       is a ValueError: False
assertRaises(ValueError) caught ValidationError: yes
assertRaises(ValueError) caught DataError: no - DataError escaped
```

The last line was the surprise: `assertRaises` does not convert a non-matching
exception into a clean assertion failure — the exception **escapes the context
manager** and fails the test as an error instead. That means a wrongly-typed
exception shows up as an ERROR in the test report rather than a FAIL, which is a
distinction I had not understood and which matters when reading a test run.

### Independent verification

The strongest check available: run the **original 41 tests, unmodified, against
the new package**, from inside the repository so they import the rewritten
`campusflow`:

```
Ran 41 tests in 0.016s

OK
```

Measured, not reasoned. That is what "no original test was weakened" means here,
and it is recorded in [baseline-check.md](baseline-check.md).

### Decision

`ValidationError(ValueError)` for anything a person can recover from.
`DataError(Exception)` — deliberately *not* a `ValueError` — for stored data that
cannot be trusted. `main.py` catches `ValidationError` to print a friendly
message, and `DataError` only around the initial load, where it offers
quit-or-start-fresh.

**Evidence: VERIFIED.**

---

## Cycle 3 — "a save that fails half way has destroyed the file"

### Concept gap

Requirements A and E both say a rejected action must leave the collection
unchanged. I had been thinking only about in-memory state. Writes are also an
action, and the original `save_json` opened the target file for writing —
truncating it — and then wrote the new contents into it. Between those two
moments the file on disk is empty or half-written.

### Question asked

> If the program is killed while `json.dump` is writing, what is left in the
> file? And does writing to a temporary file and then renaming it over the
> target actually replace the old file on Windows, or does the rename fail
> because the destination exists?

### Guidance given

Opening with `"w"` truncates immediately, so a crash mid-write leaves a
truncated or partial file, and a partial JSON file is unreadable — the next
start-up offers "start fresh", which is data loss caused by an unrelated crash.

`os.replace` is the atomic rename, and unlike `os.rename` it replaces an existing
destination. It must be on the same filesystem as the target, otherwise it is a
copy and the atomicity is gone — which is why the temporary file has to be
created in the *same directory* as the target, not in the system temp folder.

### Small experiment on unrelated ground

The claim I did not want to take on faith was "`os.replace` overwrites, and
leaves nothing behind". So: two files in one directory, replace one with the
other, then list the directory.

```
after os.replace, contents: NEW
leftover files: ['tickets.json']
```

Both halves confirmed — the target now holds the new content, and only one file
remains. No stray temporary.

### Independent verification

`tests/test_storage.py::test_saving_leaves_no_temporary_files_behind` saves a
ticket and then scans the data directory for anything with a `.tmp` suffix,
asserting the list is empty. `test_backing_up_a_file_preserves_its_contents`
covers the other half — that the "start fresh" path copies the broken file
before overwriting it, so starting fresh is recoverable.

### Decision

`save_json` creates the temporary file with `tempfile.mkstemp(dir=path.parent)`,
writes and closes it, then calls `os.replace`. If the write raises, the temporary
file is unlinked in a `finally` block so a failed save does not litter the data
folder. `load_counter` and `load_staff` still read the file directly — a reader
cannot corrupt anything.

**Evidence: VERIFIED** for the `os.replace` semantics and the leftover-file
test; **INFERRED** for "a crash leaves a truncated file", since I did not kill
the interpreter mid-write.

---

## Team section — AI suggestions that were changed or rejected

### Rejected: "make every check raise `ValidationError`"

The guidance for Cycle 2 was framed as "one new exception type would be enough".
I rejected that and kept two. The reason is the original storage code:

```python
except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
    print(f"\nError loading tickets: {error}")
```

It treats a corrupt file as if the user had typed something wrong. If the data
error had been a `ValueError` too, this handler — and any `except ValueError`
written by habit — would have gone on doing exactly that: printing a message and
carrying on with a partial collection. Making `DataError` unrelated to
`ValueError` is what turns "the file is untrustworthy" into a failure a caller
cannot miss by accident.

### Changed: "validate priority in `Ticket.__post_init__`"

The first suggestion for Requirement E was to enforce priority consistency in
the dataclass, on the grounds that the dataclass is where every other field is
checked. I measured against the existing suite first: roughly ten original test
fixtures build tickets with `urgency="medium", affected_users=5` and then pin the
priority to `high`, `critical` or `low` deliberately, because those tests are
about the *work queue ordering* and not about priority derivation. Enforcing
consistency in `__post_init__` would have failed all of them.

I moved the check to `validate_ticket_record` instead, where it runs on **load**
only. The invariant Requirement E actually asks for — a hand-edited priority must
not load silently — is still enforced, and the original tests are untouched. Both
the shipped three-ticket file and every fixture were then measured to confirm
they are consistent with the rules anyway, so nothing legitimate is rejected.
