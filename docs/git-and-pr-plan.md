# Git and PR plan — directions only

**Nothing in this document was executed.** No branch was created, nothing was
staged, no commit was made, nothing was pushed, and no issue or pull request was
opened. Every command below is written for a person to run.

Measured state at the time of writing, so the directions start from facts:

```
$ git log --oneline -4
2ab8d7b feat: enhance tests and documentation for CampusFlow Next
5abd263 Add structured notes, search functionality, and validation checks
75ffda9 refactor and enhanced CampusFlow Next codebase
0a4f00f mutable recall from initial repository campusflow-adogah (for audit and improvement)

$ git rev-list --left-right --count origin/master...master
0       0
```

`master` and `origin/master` are both at `2ab8d7b`, and there is nothing
unpushed.

**Re-measured on 2026-10-16, after `2ab8d7b` was made.** An earlier draft of this
document was written before that commit existed, and it described a much larger
set of uncommitted files. The sections below have been corrected against the tree
as it now stands — a plan built on a stale `git status` tells the owner to commit
things that are already committed.

---

## 1. Read this first: the feature work is already on `master`

The brief asks for feature branches and a PR with review before merge. None of
the feature commits went through that:

| Commit | Contents | Should have been |
|---|---|---|
| `75ffda9` | `errors`, `jsonio`, `categories`, `tickets`, `priority`, `workflow`, `validation`, `storage` — 960 insertions across 8 files | Engineer 1's branch |
| `5abd263` | `notes`, `search`, `reports`, `understanding_check`, `main`, and 9 test modules — 2733 insertions across 17 files | Engineer 2's branch |
| `2ab8d7b` | the documentation set, the `search.py` docstring fix, four test-file changes, and `data_folder/categories.json` — 1967 insertions across 14 files | a branch of its own, before merge (see §3) |

All three are on `master`, and `master` is already pushed. That is a deviation
from the brief's own process rule, and it should be named in the submission
rather than quietly ignored.

**Do not try to fix it by rewriting history.** Moving those commits onto branches
now would mean `git reset --hard` on a branch that has already been pushed, and
anyone who has fetched it would end up with a divergent `master`. The work itself
is fine; only its route is wrong.

### The two honest options

**Option A — keep the history, use a branch from here on (recommended).**
Leave the three commits where they are, and put the remaining work — the five
files in §2, which are uncommitted right now — on a feature branch with a pull
request. The submission then notes: *"three commits landed on master before the
branch workflow was set up; everything after them went through a branch and a
reviewed PR."*

**Option B — keep the history and also open a retrospective PR.**
Same as A, plus a PR whose head branch points at the current `master` tree and
whose base is `0a4f00f`, so the reviewer sees the whole change as one reviewable
diff. This gives the reviewer the surface to review without touching history. Use
this if a reviewer needs to be able to comment on the feature code.

Either way, the review itself is real work and worth doing properly — see §5.

---

## 2. What is uncommitted right now

```
$ git status --short
 M README.md
 M campusflow/categories.py
 M campusflow/jsonio.py
 M campusflow/notes.py
 M campusflow/priority.py
 M campusflow/reports.py
 M campusflow/search.py
 M campusflow/storage.py
 M campusflow/tickets.py
 M campusflow/understanding_check.py
 M campusflow/validation.py
 M campusflow/workflow.py
 M docs/ai-learning-log.md
 M docs/baseline-check.md
 M docs/git-and-pr-plan.md
 M main.py
 M tests/support.py
 M tests/test_cli.py
 M tests/test_understanding.py
```

Nineteen files, all modifications. No new files, nothing untracked. Everything
else — `campusflow/errors.py`, `campusflow/priority.py`'s neighbours, the other
test modules, the other documents — is already committed in one of the three
commits above, `data_folder/categories.json` included.

The nineteen fall into three groups, and §3 proposes one commit for each:

| Group | Files | Nature |
|---|---:|---|
| Verification corrections | 6 | docs and tests only |
| Source editing pass | 2 | presentation only |
| `from __future__ import annotations` removed | 13 | one line each, no behaviour change (2 of the 13 overlap the group above) |

What each group holds:

1. **`README.md` — the test count and the coverage table.** The suite grew from
   242 to 246 tests after this document was first drafted, so the fresh-clone
   command now says `expect: 246 tests, OK`, the per-module table says
   `test_cli` 32 rather than 28, and Engineer 2's subtotal is 86 rather than 82.
   A requirement-to-test mapping table was added so a reviewer can check coverage
   instead of counting tests. The 242 figures were true when written; they are
   not true now, which is the whole reason this file is being corrected.

2. **`docs/baseline-check.md` — one line.** `**Current:** Ran 242 tests` became
   `Ran 246 tests`. Same reason.

3. **`docs/ai-learning-log.md` — two broken links fixed.** The index links to
   `ai-learning-log(Engieneer-1).md` and `(Engieneer-2).md`. The file names
   contain parentheses, which terminate a markdown link target, so both links
   were dead. The target is now wrapped in angle brackets inside the
   parentheses — the form markdown provides for exactly this — which is what
   allows parentheses in a target. Found by resolving every relative link in
   the repository programmatically rather than by clicking them.

4. **`tests/test_cli.py` — one test made stronger, not merely longer.**
   `TestSearchByPriority.test_the_work_queue_is_not_affected` previously asserted
   that the queue printed no `" | "` rows and that three tickets existed in
   `main.state` — which does not actually check the queue. It now asserts the
   queue's real output, line for line:
   `["T2 critical open", "T3 medium open", "T1 low open"]`. Requirement D says
   the original queue must be unchanged, and this is the test that would fail if
   it changed.

5. **`docs/git-and-pr-plan.md` — this document**, re-measured after `2ab8d7b`.

6. **`tests/test_understanding.py` — one assertion's wording.** An editing pass
   over `understanding_check.py` (item 7) lowercased the re-prompt message from
   `Invalid choice...` to `invalid choice...`. The test still asserted the old
   casing, so the suite went red on exactly that one assertion — 245 of 246, and
   reproducible in isolation, which is what made it a one-line fix rather than a
   hunt. The assertion now matches the code. It still proves what it always
   proved: an invalid choice is rejected and the same question is asked again,
   twice in the scripted run.

7. **`campusflow/understanding_check.py` and `campusflow/categories.py` — an
   editing pass over the source.** Module and function docstrings were removed
   and several user-facing prompt strings were lowercased. Checked against
   `HEAD` with `ast`: **no function or class was removed or added** in either
   file, so the change is presentation only, and no document quotes any of the
   strings that moved. Worth stating plainly because a reviewer diffing these
   two files will see a large deletion count and should know it is docstrings,
   not logic.

8. **`from __future__ import annotations` removed from all 13 files that had
   it.** One line each, plus the blank line it left doubled in eleven of them.
   The import was inert: the interpreter here is CPython 3.14, where PEP 649
   defers annotation evaluation anyway, and the two things it exists to enable —
   builtin generics (`list[str]`, 3.9+) and PEP 604 unions (`Path | None`,
   3.10+) — are native. Checked before removing, not after:

   - no `typing.get_type_hints`, no `__annotations__` access, no `TYPE_CHECKING`
     block, no `pydantic`/`attrs` in the tree, so nothing evaluates annotations
     at runtime;
   - an `ast` pass over all 13 files found **no annotation naming a symbol that
     is not bound at module scope**, so there is no forward reference or
     import-cycle workaround relying on the deferred evaluation the import
     provides — which is the one case where removing it would break a file.

   Then verified by running: 246 tests, OK, and all 13 modules import cleanly.
   The PEP 604 annotations now resolve to real union objects
   (`Ticket.__annotations__["assigned_to"]` is `str | None`, not `'str | None'`).

   **One caveat worth knowing.** The floor for running this project is now
   Python **3.10**, set by the three files that use `|` in an annotation
   (`jsonio.py:80`, `storage.py:72`, `tickets.py:277`). On 3.9 those three would
   raise `TypeError` at import; the other ten are fine back to 3.9. The README
   says only "Python 3", so nothing contradicts this — but if the marker ever
   needs to run on 3.9, restore the import in those three files and nowhere
   else.

Two things an earlier draft of this section asked the owner to decide, both now
settled by `2ab8d7b` and left here so the record is not silently rewritten:

- **`data_folder/categories.json` was committed**, alongside the other three
  tracked data files. That is the consistent choice, and it is what makes the
  README's §5 claim that `categories.json` is part of the format true. No
  `.gitignore` change was needed or made.
- **`campusflow/search.py`'s docstring fix and the 222 new lines in
  `docs/design-decisions.md`** are committed. The design-decisions diff still
  contains zero removed lines, so the file's own "do not delete, only add to
  this" instruction was respected.

---

## 3. Branch and commit directions

Run the verification in §4 first. If it fails, the commit is not ready.

### Branch

```bash
git switch -c feat/final-verification-pass
```

Branch names are suggestions; the only hard rule is that the work does not land
on `master` again.

### Commit 1 — the verification corrections

The numbers the suite outgrew, two dead links, and two tests brought back in line
with the code.

```bash
git add README.md docs/baseline-check.md docs/ai-learning-log.md docs/git-and-pr-plan.md tests/test_cli.py tests/test_understanding.py
git commit
```

Suggested message:

```
docs: correct the test count, fix two links, align two tests

The suite reached 246 tests after the documentation was first written, and
two claims in it had gone stale:

- README.md and baseline-check.md said 242 tests and gave test_cli 28 of
  them. Both now say 246 and 32. The README also gained a
  requirement-to-test mapping table, so a reviewer can check coverage
  rather than count tests.
- ai-learning-log.md linked to files whose names contain parentheses, which
  terminate a markdown link target. Both links were dead; the targets are
  now angle-bracketed.

Two tests had drifted from the code they check:

- test_cli.py: test_the_work_queue_is_not_affected asserted that the queue
  printed no search rows and that three tickets existed, neither of which is
  the queue's behaviour. It now asserts the queue's real output line for
  line. Requirement D says the original queue must not change, and this is
  the test that would fail if it did.
- test_understanding.py: asserted the capitalised re-prompt message, which
  the source no longer emits. Now matches. The test still proves an invalid
  choice is rejected and re-asked.

git-and-pr-plan.md is re-measured against the tree as it actually stands;
an earlier draft listed files as uncommitted that are not.

No application behaviour changed. Suite: 246 tests, OK.

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### Commit 2 — the source editing pass

Separate commit, because it is a different kind of change: presentation only,
over the source rather than the docs, and it should be reviewable as such.

```bash
git add campusflow/categories.py campusflow/understanding_check.py
git commit
```

Suggested message:

```
style: trim module and function docstrings; lowercase prompt strings

Docstrings removed from categories.py and understanding_check.py, and
several user-facing prompts lowercased.

Presentation only: no function or class was removed or added in either
file (checked with ast against HEAD), and nothing imports differently.
Suite unchanged at 246 tests, OK.

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### Commit 3 — drop the inert `__future__` import

Last, and separate again, so the one-line-each nature of it is obvious in the
log. `campusflow/categories.py` and `campusflow/understanding_check.py` are
already staged by commit 2; this stages the other eleven.

```bash
git add campusflow/jsonio.py campusflow/notes.py campusflow/priority.py campusflow/reports.py \
        campusflow/search.py campusflow/storage.py campusflow/tickets.py \
        campusflow/validation.py campusflow/workflow.py main.py tests/support.py
git commit
```

Suggested message:

```
style: remove the inert `from __future__ import annotations`

Removed from all 13 files that carried it. The import was doing nothing:
this runs on CPython 3.14, where PEP 649 defers annotation evaluation
regardless, and both things the import enables — builtin generics and
`X | None` unions — are native well before that.

Checked before removing, not after:

- nothing in the tree calls typing.get_type_hints, reads __annotations__,
  or uses TYPE_CHECKING, pydantic or attrs, so no annotation is evaluated
  at runtime;
- an ast pass found no annotation naming a symbol unbound at module scope,
  so no forward reference depends on deferred evaluation.

Verified by running: 246 tests OK, all 13 modules import cleanly, and the
unions now resolve to real objects rather than strings.

Sets the minimum interpreter at Python 3.10, from the three files using
`|` in an annotation. Documented in docs/git-and-pr-plan.md.

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

`data_folder/categories.json` is already committed in `2ab8d7b`, so there is
nothing to decide there and nothing to stage.

### Push and pull request

```bash
git push -u origin feat/final-verification-pass
```

Then open a PR against `master` with the three commits above. Suggested PR body:

```
## What

The final verification pass for the CampusFlow Next sprint: stale test counts
corrected, two dead documentation links fixed, two tests aligned with the code
they check, an editing pass over two source modules, and the inert
`from __future__ import annotations` removed from all 13 files that had it.
No behaviour change to the application itself.

## Evidence

- `python -m unittest discover -s tests -v` → 246 tests, OK
- the original 41 tests, unmodified, against the rewritten package → OK
- `data_folder/tickets.json` written by the first version still loads: three
  tickets, `assigned_to: false` read as unassigned, missing `notes` keys
  defaulting to empty

## Deviations from the brief

`75ffda9`, `5abd263` and `2ab8d7b` were committed directly to `master` before
the branch workflow was in place, and `master` is already pushed. Rather than
rewrite pushed history, this PR carries the remaining work and the deviation is
recorded here as well as in `docs/git-and-pr-plan.md`.

## Not done by the author

No branch, commit, push, issue or PR was created by the AI assistant working on
this sprint; it was asked to write code and documentation only. The commands
are directions in `docs/git-and-pr-plan.md`, run by the repository owner.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 4. Verify before every commit

```bash
python -m unittest discover -s tests -v      # expect: 246 tests, OK
```

Expected output, with nothing after `OK` — a stray line from any function that
prints during a test is a signal that output is leaking somewhere it should not:

```
Ran 246 tests in 0.1XXs

OK
```

Two further checks worth running by hand, because they exercise paths the suite
does not:

```bash
# the shipped data still loads, in its original format
python -c "from campusflow import storage; d = storage.load_application_data(); print(list(d.tickets), d.warnings)"

# a fresh install: an empty data folder reports 0% rather than raising
python -c "from campusflow.reports import generate_report, print_report; print_report(generate_report({}))"
```

---

## 5. Issues and reciprocal review

The brief asks for GitHub Issues and a PR reviewed by the other engineer before
merge. Suggested issues, in the order the work actually happened:

| # | Title | Owner | Labels |
|---|---|---|---|
| 1 | Centralise validation; reject invalid input without changing state | Engineer 1 | `requirement-a` |
| 2 | Add structured follow-up notes (`N001`…) with validate-before-mutate | Engineer 1 | `requirement-b` |
| 3 | Read-only search with AND filters and re-prompting | Engineer 2 | `requirement-c` |
| 4 | Reports: by category, unresolved/resolved, resolution % | Engineer 2 | `requirement-d` |
| 5 | Strict all-or-nothing loading; extended data file format | Engineer 1 | `requirement-e` |
| 6 | Engineering understanding check | Engineer 2 | `check` |
| 7 | Test Lab: 14+ tests, 5 per engineer, 2 bug-hunter | both | `tests` |

### What a reviewer should actually check

Not "does it run" — the suite answers that. These are the things a green suite
does not prove:

1. **Reviewer of Engineer 1's code:** pick a field check at random, give it a
   value the tests do not use, and confirm the failure message names the value
   and the legal options. Then confirm `ValidationError` is still a `ValueError`
   subclass — if that ever changes, 41 original tests break silently.
2. **Reviewer of Engineer 2's code:** press Enter at every search prompt and
   confirm the result is *every* ticket, then type a space and Enter, and
   confirm it is still every ticket. That second one is the trap the truthiness
   experiment caught.
3. **Both:** open `data_folder/tickets.json` by hand, change one `priority` to
   something the rules do not imply, and start the app. It must refuse the load
   and offer quit-or-start-fresh rather than loading the wrong priority.
4. **Both:** confirm the Open Work Queue still shows `open` plus `in_progress`
   and nothing else. It was required to be unchanged, so "it looks reasonable"
   is not the test.
5. **Both:** check that every claim in the docs that says "measured" has a
   command or an output beside it. This sprint's whole submission rests on that
   distinction.

Approval is given by the other engineer on the PR, and only then is it merged.
Per the brief, the owner merges — the reviewer approves.
