# CampusFlow — Worded Implementation Guide

**Context:** This guide supports [docs/design-decisions.md](docs/design-decisions.md). It describes in plain English what each piece of the code should do, so the owner can write the code and tests by hand. A few broken bits in the current draft files are flagged at the end.

---

## tickets.py — the dataclass and the field checks (docs §1.2, 1.2b)

**The two lists at the top.** Start the file by writing down the two lists of allowed values as module-level names — one list of categories, one list of urgencies. Pick one canonical spelling for each and keep it lowercase. The lowercase matters because `priority.py` compares urgency against lowercase text ("high", "medium"), so your urgency list has to be lowercase or the two modules will never agree.

**The four field checks.** All four take the rawest possible input — a string straight from the user — clean it, and hand back the correctly-typed value. That way both the dataclass and the menu can call the same checks, and validation is never written twice.

- **Title.** Take the text the user typed and strip the extra spaces off the front and back. Then look at what remains: if nothing is left, raise an error telling the user the title cannot be blank. This has to catch a title that is only spaces too, so do the stripping *before* you test — a string of spaces is non-empty but still blank. If something is left, return the cleaned-up title as the value to store.
- **Category.** Compare what the user typed against the allowed category list, ignoring uppercase and lowercase. When it finds a match, return the official spelling *from the list* — not whatever the user typed. That is how network, Network and NETWORK all end up stored as the same value. If nothing matches, raise an error that names the valid options.
- **Urgency.** The same idea as the category check, but matched against the urgency list, and it always returns the lowercase form.
- **Affected users.** This one is different because it has to convert as well as validate: the input arrives as text. First try to turn it into a whole number. If the conversion fails because the text isn't numeric, raise an error saying the value must be a whole number — don't let a raw conversion error escape. Then check the sign: the design doc says the count must be a *positive* whole number, so reject anything less than one. Return the number once it's valid.

The shape to keep in mind: these checks raise errors rather than returning some "it failed" flag. Raising is what stops a bad ticket from ever being built.

**The dataclass.** Declare it with the eight fields in the doc's order: id, title, category, urgency, affected_users, priority, status, assigned_to. Two of those carry defaults — status starts as "open" and assigned_to starts empty — so they belong at the end, after the fields that don't have defaults. Put a defaulted field in the middle and the dataclass will refuse to build at all.

- `priority` is a plain required text field. It is *not* computed inside the dataclass — the create flow in `main.py` works out the priority first (using `priority.py`) and passes it in, which matches F1's "calculate priority" step. (Note: the current draft of this field is broken — see the flags at the end.)
- Decide whether the dataclass is frozen or not. Tickets get modified after creation — the workflow changes status, assignment sets who it's handed to — so a normal, non-frozen dataclass is the simpler fit: you can just assign a field instead of building a replacement object every time.
- Write the `__post_init__` method, the hook that runs automatically right after construction. Inside it, run each of the four checks against its field and save the returned (cleaned) value back onto that field. Because any failing check throws from inside this method, construction aborts and no half-valid ticket is ever handed back. That is the "a bad ticket can never be created" guarantee, and it only holds if every check runs in here.
- Don't validate the id. It comes from the counter in `storage.py`, never from a user, so there's nothing to correct and nobody to show an error to.

---

## priority.py — the priority rules (docs §1.3, 1.3a, 1.3b)

This one is already written, but these are the rules to keep matching:

- Name the two thresholds at the top of the file — the critical user count (10) and the affected-users threshold (3) — and use those names in the conditions instead of scattering raw numbers around, so a policy change later is one edit.
- The function takes urgency first, then the count of affected users.
- **Rule 1:** if the urgency is "high" *and* the count is 10 or more, it's **critical**.
- **Rule 2 (else if):** if the urgency is "high" *or* the count is 10 or more, it's **high**. Understanding the trap here: rule 2 is deliberately broader than rule 1 — rule 1 is exactly rule 2 with "and" swapped for "or" — so every critical ticket would also satisfy rule 2. The only reason critical is ever returned is that rule 1 sits *above* rule 2 and returns first. If you ever swap these two, critical becomes unreachable.
- **Rule 3 (else if):** if the urgency is "medium" *or* the count is 3 or more, it's **medium**. The subtle part: the user threshold here is 3, which is lower than rule 2's 10, so a medium-urgency ticket affecting ten people satisfies this rule but never reaches it — rule 2 already caught it and returned high. That's intended: enough affected people outweigh the urgency.
- **Final else:** return **low**, with no condition. The bare else is what guarantees nothing falls through the chain.
- Don't lowercase or re-validate the urgency inside — by the time this runs, the input has already been normalised upstream. And return exactly the four spellings — critical, high, medium, low — because the work queue maps those same words to sort ranks.

---

## workflow.py — status moves (F4), assignment (F3), work queue (F5)

**The status-move table.** Keep a table of the only allowed status moves:

- an **open** ticket can move to **in_progress**,
- an **in_progress** ticket can move to **resolved**,
- a **resolved** ticket can move back to **open**, and only as an explicit reopen.

There are no other moves. In particular an in_progress ticket can never go back to open.

**Deciding whether a move is allowed.** Look at the ticket's current status, consult the table for what it's allowed to become, and check the requested new status is one of those. On top of the table, one more rule: a ticket that has no one assigned is not allowed to move into in_progress.

**Assignment.** The user picks a staff member from the saved staff list. If the ticket is resolved, refuse to assign it until it is reopened. Otherwise set the ticket's assigned_to field. Unknown ticket IDs are rejected by the caller before this runs. Tickets are kept in a dictionary keyed by id, so looking one up is instant.

**The work queue.** Show the tickets whose status is open or in_progress. Sort them with a two-part key: first the priority rank, then the ticket number. The ranks are fixed — critical is 0, high is 1, medium is 2, low is 3. The number inside the id (the 12 in T012) has to be pulled out and sorted as a number, not as text — otherwise T100 sorts before T20.

---

## storage.py — persistence (docs F7)

**The three files.** Everything lives inside a `data/` folder: `tickets.json` (the tickets), `counter.json` (the latest id number), and `staff.json` (the staff list).

**Loading tickets.** Read the tickets file. If the file doesn't exist — a first run — start with an empty set of tickets. If the file is broken — bad JSON, or a ticket that fails the dataclass checks when rebuilt — show the user the error and ask whether to quit or start fresh. If they choose fresh, first copy the broken file to a backup name so nothing is lost, then start from empty.

**The id counter.** `counter.json` holds the highest id issued so far. On a first run with no file, treat it as zero so the first ticket comes out as T001. To issue a new id: take the counter's current value, add one to get the new number, form the id from it, and save the counter at its new value. An id is never reused, even if the ticket itself is later deleted or modified.

**The staff list.** On a first run, create `staff.json` with a few placeholder names so the app is usable straight away. For now the list is edited by hand.

**The counter check at startup.** Compare the counter value against the highest ticket id already saved. If the counter is missing, or lower than the highest ticket id, show a warning and ask the user to fix it or quit.

**Saving.** Save after every change — every modify, create, or assignment writes the affected file back.

---

## reports.py — the two functions (docs F6)

Two separate functions. One *works out the numbers* and returns them without printing anything: the total count of tickets, the count of tickets by each status, and the count of tickets by each priority. The other *takes those numbers and prints them*. When the set of tickets is empty, print a "no tickets yet" message instead.

---

## main.py — the menu, create (F1), list/view (F2) (docs §1.5, M1)

**The menu.** Build it from a list of (label, action) pairs — the same list both writes the menu text the user sees and dispatches the number they pick. Adding a menu option later is one new entry, and the displayed menu can never drift away from the actions that exist.

**Create (F1).** Ask for one field at a time — title, then category, then urgency, then affected users. For each field, keep re-asking *only that field* until it passes its check. Once all four are valid: work out the priority from the urgency and the user count, generate the next id from the counter, build the ticket, add it to the dictionary, save, and confirm what was created.

**List / View (F2).** Two steps. First print a short row per ticket — id, title, priority, status. Then ask the user for an id: if it isn't a known ticket id, reject it; otherwise print the full details of that ticket.

**The main loop.** Load the tickets, staff list and counter at startup, run the counter-vs-tickets check, then loop until the user quits: show the menu, read the choice, and call the matching action — which includes assign, change status, work queue, and reports alongside create and list.

---

## Tests — what each file should cover (docs §1.5, M3, `unittest`)

Any test that touches files uses a temporary folder, so the real `data/` files are never disturbed.

- **test_tickets:** for each of the four checks — a valid input, a case-variation input where you assert the normalised value comes back (the test that catches a check which validates but forgets to return the canonical form), and an invalid input where you assert it raises. Plus: a good ticket builds with normalised fields, and a bad field raises and leaves no object behind.
- **test_priority:** one test per rule, and make sure the boundary rows are in there, not just the easy ones — high with exactly 10 users gives critical (not 9), medium with 10 users gives high (rule 2 catches it before rule 3), medium with exactly 3 gives medium (not 2). Those are the rows that catch a wrong comparison operator or the two rules in the wrong order.
- **test_workflow:** each allowed move passes; the forbidden moves fail (an in_progress ticket cannot go back to open); an unassigned ticket cannot move to in_progress; a resolved ticket refuses assignment until reopened; the queue sorts by priority then by numeric id — include a T100-versus-T20 case so the numeric sort is actually exercised.
- **test_storage:** saving then loading comes back with the same tickets; a first run with no files starts clean; a broken file triggers the error-and-ask behaviour; the counter-vs-tickets mismatch warning fires.
- **test_reports:** an empty set prints the "no tickets yet" message; a non-empty set gives the right totals by status and by priority.

---

## Small things to tidy up as you go

1. **The misnamed file.** There's a file called ` workflow.py` — with a leading space in its name. The design doc calls for `workflow.py`. Rename it (and build F3/F4/F5 into the correctly-named file).
2. **The broken annotation in tickets.py.** The `priority` field is currently written as `priority: str | "low"`, and that crashes the import — a plain text type with a default value is not valid there as written, and it isn't a default anyway. Give priority a plain required text type.
3. **The affected-users sign rule.** The current draft only rejects negative numbers, which lets zero through. The design doc says "positive integer", and your own implementation log states zero is not allowed — the check should hold zero back too, and the "zero case" deserves a test of its own, since that's where the off-by-one lives.
4. **test_reports.py doesn't exist yet** — it's listed in the layout, so it needs creating alongside the other four test files.
