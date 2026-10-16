# AI learning log — Engineer 2 (Search, Reporting and CLI)

Three cycles, recorded in the brief's format: **concept gap → the exact question
asked → what the AI guidance said → a small experiment on unrelated ground →
independent verification against the real code → decision.**

The AI was used to explain a concept, then every claim was checked by running
something. Two suggestions that did not survive that check are in the team
section at the end.

Areas owned in this sprint: `search.py`, `reports.py`, `main.py`,
`understanding_check.py`, and the CLI-facing behaviour of the note menus.

---

## Cycle 1 — "blank means no filter, and I nearly got that wrong"

### Concept gap

Requirement C says a blank filter means "do not filter on this field", while a
supplied filter must match. My first instinct was to test the filter with
Python's truthiness — `if title_query:` — because `None` and `""` are both falsy,
so that looked like it covered both "not supplied" and "supplied blank".

I could not say what happens to a filter that is *only spaces*. I had a suspicion
that `bool("   ")` is not what I wanted, but I could not state it.

### Question asked

> Requirement C says a blank filter is ignored. Is `if value:` the right test for
> "the user supplied a filter"? What is the difference between a filter that is
> `None`, one that is `""`, and one that is `"   "`?

### Guidance given

`bool("   ")` is `True`. Python strings are falsy only when they are empty, so a
whitespace-only string is truthy and `if value:` would treat it as a real
filter — searching for a title containing three spaces, which matches nothing
and looks to the user like a bug in the search. The correct order is to strip
first and then test: `value.strip()` is what decides "blank", and the stripped
value is what gets used.

The guidance also pointed out that this must happen in **one** place, not at each
call site, or the CLI and the search function will eventually disagree about what
"blank" means.

### Small experiment on unrelated ground

Whether truthiness is really as simple as "empty string is falsy" — I tested it
against `None` as well, since the CLI has to handle both:

```
''       truthy=False   'if value' -> no filter
'   '    truthy=True    'if value' -> filter
None     truthy=False   'if value' -> no filter
```

The middle line is the trap, measured rather than assumed. `'   '` would have
been treated as a filter.

### Independent verification

The rule now lives in one function, `_normalise_filter` in `validation.py`:

```python
if raw_value is None:
    return None
if isinstance(raw_value, str) and not raw_value.strip():
    return None
```

Three tests hold it: `test_blank_filters_mean_do_not_filter`,
`test_blank_title_does_not_filter` (a title of three spaces returns every
ticket), and — the one that matters for the CLI — `ask_filter` returns `None`
for a blank answer and re-prompts for an unrecognised one, so an invalid option
cannot quietly become an empty result list. Covered by
`test_a_blank_search_filter_means_do_not_filter` and
`test_an_invalid_search_filter_re_prompts`.

### Decision

Blank is decided by `strip()`, in `validation._normalise_filter` for the
category/status/priority filters and in `search_tickets` for the title. The CLI
calls the same helper, so pressing Enter at every prompt genuinely means "no
filter" and does not depend on which menu the user came through.

**Evidence: VERIFIED.**

---

## Cycle 2 — "the report has to answer 0% on an empty list"

### Concept gap

Requirement D asks for a resolution percentage, `resolved / total * 100`, and
also says an empty dataset must report 0% without a division error. I understood
the requirement but not where the failure would land — my assumption was that
`print_report` already had an early return for the empty case, so the guard was
somewhere else in the pipeline.

### Question asked

> Where should the zero guard go so that an empty report cannot raise? Does it
> belong in `generate_report`, in `print_report`, or in both — and what does
> `round` do to a percentage that does not divide evenly?

### Guidance given

The guard belongs in `generate_report`, because that is the function that owns
the number. My assumption about `print_report` was wrong in a way worth naming:
`print_report(generate_report({}))` calls `generate_report` **first**, so an
early return inside `print_report` cannot prevent the division — it runs after
the damage. And the number is needed independently of display anyway, which the
tests demonstrate by reading `report["resolution_percentage"]` directly without
printing anything.

The guidance also warned against `total - resolved` for the unresolved count,
even though it gives the same answer for these three statuses, because it is only
correct while every ticket has exactly one of "resolved" and "not resolved".

### Small experiment on unrelated ground

What `round` does to a repeating percentage, which is unrelated to empty lists
but decides how the number is displayed:

```
2/3*100       = 66.66666666666666
round(..., 1) = 66.7
1/1*100       = 100.0 -> 100.0
```

`round(x, 1)` returns a float, so the displayed value is `100.0` and not `100`.
That matters because the empty-report line has to read `0.0%` to match, and
`str(0.0)` is `"0.0"` while `str(0)` is `"0"`. Writing the empty case as `0`
would have produced a report whose two percentage lines did not look alike.

### Independent verification

`generate_report` computes the percentage with an explicit conditional:

```python
"resolution_percentage": (round(resolved / total * 100, 1) if total else 0.0),
```

The naive version was measured, not imagined:

```
BH-2 naive percentage raises: ZeroDivisionError division by zero
```

The empty case is pinned by `test_resolution_percentage_is_zero_not_a_crash`
(recorded as bug-hunter test **BH-2**) and by
`test_printing_an_empty_report_says_so_and_shows_zero`. The `total - resolved`
temptation is closed off by `test_status_counts_add_up_to_the_total`, which
asserts `unresolved + resolved == total` **and**
`sum(by_status.values()) == total` — so a status counted twice, or a fourth
status added later, fails the suite instead of skewing the report.

### Decision

Zero guard in `generate_report`, because that is the function that owns the
number. `print_report` keeps its original early return and gains a single
resolution line, so the empty screen reads:

```
No tickets yet.
Resolution: 0.0% (0 of 0 resolved)
```

I had assumed the early return was the thing standing between the app and a
crash, and it was not — the crash was in the function that computes the number,
which the early return never reached. Removing the early return would have
changed screen output that the brief requires to be preserved, to solve a
problem that was somewhere else. Keeping it means the change is one added line,
and `test_empty_prints_no_tickets_yet` still asserts the original sentence.

**Evidence: VERIFIED.**

---

## Cycle 3 — "case-insensitive is not quite `lower()`"

### Concept gap

Requirement C says the title search is case-insensitive. `str.lower()` is the
obvious tool and is what I would have written without thinking. I could not say
whether there are strings where `lower()` fails to make two equal-in-intent
strings compare equal.

### Question asked

> Is `str.lower()` sufficient for a case-insensitive substring search, or is
> `str.casefold()` the right choice? Where exactly is the difference observable?

### Guidance given

`casefold()` is the operation intended for caseless comparison, and `lower()` is
the operation for display. The observable difference is characters whose case
mapping is not one-to-one — the German eszett `ß` being the standard example:
`"ß".lower()` is `"ß"`, but `"ß".casefold()` is `"ss"`, so a user who types
`STRASSE` would not find a title stored as `Straße` under `lower()`, but does
under `casefold()`.

### Small experiment on unrelated ground

Whether the difference is real on this Python build, including a Turkish-dotted
capital I, which I expected to be a second case of the same problem:

```
eszett             lower()='\xdf'      casefold()='ss'
dotted capital I   lower()='i̇'   casefold()='i̇'
'STRASSE'.lower()    = strasse
'STRASSE'.casefold() = strasse
does STRASSE find 'straße' with lower():    False
does STRASSE find 'straße' with casefold(): True
```

The eszett behaves as described. The dotted capital I does **not** differ between
the two methods on this build — my expectation of a second example was wrong, and
having tested it stopped me writing a comment that would have been false.

### Independent verification

`search.py` compares with `casefold()` on both sides:

```python
def _matches_text(haystack, needle) -> bool:
    return needle.casefold() in haystack.casefold()
```

`test_matches_a_substring_with_different_case` and
`test_ignores_case_in_both_directions` cover the ordinary cases. The same
experiment also produced a limit worth naming: `WIFI` does **not** find `Wi-Fi`,
because this is substring matching and not fuzzy matching — pinned deliberately
by `test_does_not_fuzzy_match_across_punctuation`, since the brief rules out
promising spelling correction.

### Decision

Comparison uses `casefold()`; storage keeps `.lower()`.

That asymmetry is real and was found by this experiment, not designed. I kept it
after checking the consequence: the title is stored `lower()`ed, but search
casefolds *both* the stored title and the query, so a `ß` in a stored title still
matches a `ss` in a query. Changing storage to `casefold()` would rewrite the
titles of tickets that already exist — turning `straße` into `strasse` on disk —
for no change in search behaviour. Smallest change that satisfies the
requirement, so storage stays as it was.

**Evidence: VERIFIED** for the casefold/lower difference and the search
behaviour; **OBSERVED** that no test depends on the stored form for non-ASCII
titles.

---

## Team section — AI suggestions that were changed or rejected

### Rejected: "`if value:` is enough to detect a blank filter"

Cycle 1's first suggestion was to rely on truthiness of the filter value, on the
grounds that both `None` and `""` are falsy. The measurement in the cycle above
shows the gap: `"   "` is truthy, so a user who pressed the space bar and then
Enter would have got a filter for a string of spaces and an empty result list —
the exact opposite of the documented "blank means no filter". Replaced with
strip-then-test in one shared helper.

The same rejection applies more widely: `main.ask_filter` returns `None` for a
blank answer, so the search functions receive `None` rather than `""` and there
is only ever one representation of "no filter" in the program.

### Changed: "reject a note before checking whether it is allowed"

The original ordering for Requirement B's note flow checked the author and the
message first, and only then asked whether the ticket accepts notes at all. On a
*resolved* ticket that means a user types a name and a message and is then told
the ticket cannot take a note — the work is thrown away, and the message reads as
a complaint about the note rather than about the ticket's state.

Changed the order in `notes.add_note` so the status check runs first:

```python
if not notes_allowed(ticket):
    raise ValidationError(f"Ticket {ticket.id} is {ticket.status}. A note can only be "
                          "added to an open or in-progress ticket; reopen it first.")
clean_author = check_note_author(author)
clean_message = check_note_message(message)
note_id = next_note_id(ticket)
```

Nothing is written between the first check and the last, so a rejection still
leaves the ticket byte-for-byte unchanged — which is what
`TestRejectedNotesChangeNothing` asserts, including that a refused note does not
consume a note ID. The reordering only changes *which* message the user sees
first, and the user sees the useful one.
