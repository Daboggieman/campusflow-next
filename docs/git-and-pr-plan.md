# Git and PR plan — directions only

**Nothing in this document was executed.** No branch was created, nothing was
staged, no commit was made, nothing was pushed, and no issue or pull request was
opened. Every command below is written for a person to run.

Measured state at the time of writing, so the directions start from facts:

```
$ git log --oneline -3
5abd263 Add structured notes, search functionality, and validation checks
75ffda9 refactor and enhanced CampusFlow Next codebase
0a4f00f mutable recall from initial repository campusflow-adogah (for audit and improvement)

$ git rev-list --left-right --count origin/master...master
0       0
```

`master` and `origin/master` are at the same commit and there is nothing unpushed.

---

## 1. Read this first: the feature work is already on `master`

The brief asks for feature branches and a PR with review before merge. The two
feature commits did not go through that:

| Commit | Contents | Should have been |
|---|---|---|
| `75ffda9` | `errors`, `jsonio`, `categories`, `tickets`, `priority`, `workflow`, `validation`, `storage` — 960 insertions across 8 files | Engineer 1's branch |
| `5abd263` | `notes`, `search`, `reports`, `understanding_check`, `main`, and 9 test modules — 2733 insertions across 17 files | Engineer 2's branch |

Both are on `master`, and `master` is already pushed. That is a deviation from
the brief's own process rule, and it should be named in the submission rather
than quietly ignored.

**Do not try to fix it by rewriting history.** Moving those commits onto branches
now would mean `git reset --hard` on a branch that has already been pushed, and
anyone who has fetched it would end up with a divergent `master`. The work itself
is fine; only its route is wrong.

### The two honest options

**Option A — keep the history, use a branch from here on (recommended).**
Leave `75ffda9` and `5abd263` where they are, and put the remaining work — the
documentation, the `search.py` comment fix and the four test-file changes that
are currently uncommitted — on a feature branch with a pull request. The
submission then notes: *"the two feature commits landed on master before the
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
 M campusflow/search.py
 M docs/ai-learning-log(Engieneer-1).md
 M docs/ai-learning-log(Engieneer-2).md
 M docs/design-decisions.md
 M tests/test_cli.py
 M tests/test_search.py
 M tests/test_storage.py
 M tests/test_workflow.py
?? data_folder/categories.json
?? docs/ai-learning-log.md
?? docs/baseline-check.md
?? docs/bug-hunter-tests.md
```

Four things worth knowing about these:

1. **`docs/ai-learning-log(Engieneer-1).md` and `(Engieneer-2).md` are tracked
   but were empty.** They are in the tree from `0a4f00f` with zero bytes. They
   have been filled in, not created. The file names — including the "Engieneer"
   spelling — are the ones the repository already had, and were left alone.

2. **`data_folder/categories.json` is new and untracked.** It was written by
   running the loader during verification, not authored by hand. Its content is
   the five default categories:

   ```json
   {"active": ["network", "hardware", "software", "administrative", "other"],
    "retired": []}
   ```

   `data_folder/` is **not** in `.gitignore`, and the other three data files
   (`tickets.json`, `counter.json`, `staff.json`) are tracked. So this file can
   be committed with them, and documenting it in the README (§5 of the README)
   is only true if it is. **Decision for the owner:** commit it for consistency
   with the other three, or add `data_folder/` to `.gitignore` and stop tracking
   all four — but do not leave this one file as the odd one out, because the
   README documents it as part of the format.

3. **`campusflow/search.py` is a comment-only change.** The docstring for
   `_matches_text` claimed `casefold()` handles "dotted/dotless I in Turkish
   text". An experiment in [ai-learning-log(Engieneer-2).md](ai-learning-log(Engieneer-2).md)
   showed the dotted capital İ maps identically under `lower()` and `casefold()`
   on this build, so the claim was false. The docstring now names the eszett,
   which is a real difference, and `test_folds_the_case_mappings_that_lower_leaves_alone`
   pins it. No behaviour changed.

4. **`docs/design-decisions.md` gained 222 lines and lost none.** Verified: the
   diff contains zero removed lines. The file's own instruction — "do not
   delete, only add to this" — is respected, and the original decisions are
   untouched above the new section.

---

## 3. Branch and commit directions

Run the verification in §4 first. If it fails, the commit is not ready.

### Branch

```bash
git switch -c feat/docs-and-verification
```

Branch names are suggestions; the only hard rule is that the work does not land
on `master` again.

### Commit 1 — the documentation set

```bash
git add docs/baseline-check.md docs/bug-hunter-tests.md
git add docs/ai-learning-log.md "docs/ai-learning-log(Engieneer-1).md" "docs/ai-learning-log(Engieneer-2).md"
git add docs/design-decisions.md README.md
git commit
```

Suggested message:

```
docs: baseline check, bug-hunter write-ups, learning logs, README

Adds the evidence the brief asks for, all measured in this environment
rather than recalled:

- baseline-check.md: the 41-test baseline at 0a4f00f, five inputs the
  original code got wrong, and the 15 audit findings mapped to the tests
  that now cover them. Includes running the original 41 tests unmodified
  against the rewritten package — all pass.
- bug-hunter-tests.md: BH-1 (json.load keeps the last of two identical
  keys, so a duplicated ticket ID lost a ticket with no error) and BH-2
  (the resolution percentage on an empty dataset).
- ai-learning-log.md plus one log per engineer, three cycles each, each
  with a measurement and with an AI suggestion that was changed or
  rejected after being run.
- design-decisions.md: 15 new decisions appended. The diff removes no
  lines, so the original decisions are intact.
- README.md: documented data formats, the notes and search behaviour, the
  priority-consistency load invariant, the T1 vs N001 ID conventions, and
  fresh-clone instructions.

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### Commit 2 — the two test-run fix-ups

```bash
git add tests/test_cli.py tests/test_workflow.py tests/test_search.py tests/test_storage.py campusflow/search.py
git commit
```

Suggested message:

```
test: CLI and lifecycle coverage, plus a clean test run

- test_cli.py: menu shape, the input loops (re-prompting, blank filters,
  unknown ticket IDs), and the rejected-action cases that must leave the
  collection unchanged.
- test_workflow.py: the full 3x3 can_transition matrix, so pinning the
  predicate pins the rule.
- test_search.py: casefold coverage — STRASSE finds a title stored as
  Straße, which lower() would miss.
- test_storage.py: capture the backup path print so the suite's own output
  is not misleading.
- search.py: correct a docstring that claimed casefold handles Turkish
  dotted I. It does not; the eszett is the real example. Comment only.

Suite: 242 tests, OK.

Co-Authored-By: Claude Code <noreply@anthropic.com>
```

### The data file

If the owner decides to commit `data_folder/categories.json`, add it to commit 1
with `git add data_folder/categories.json`. If not, add `data_folder/` to
`.gitignore` in a **separate** commit that also removes the other three, and say
so in the submission — a half-tracked data folder is worse than either option.

### Push and pull request

```bash
git push -u origin feat/docs-and-verification
```

Then open a PR against `master` with the two commits above. Suggested PR body:

```
## What

Documentation and verification for the CampusFlow Next sprint, plus two
test-run fix-ups. No behaviour change to the application itself.

## Evidence

- `python -m unittest discover -s tests -v` → 242 tests, OK
- the original 41 tests, unmodified, against the rewritten package → OK
- `data_folder/tickets.json` written by the first version still loads: three
  tickets, `assigned_to: false` read as unassigned, missing `notes` keys
  defaulting to empty

## Deviations from the brief

`75ffda9` and `5abd263` were committed directly to `master` before the branch
workflow was in place, and `master` is already pushed. Rather than rewrite
pushed history, this PR carries the remaining work and the deviation is
recorded here.

## Not done by the author

No branch, commit, push, issue or PR was created by the AI assistant; the
commands are in `docs/git-and-pr-plan.md` and were run by hand.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 4. Verify before every commit

```bash
python -m unittest discover -s tests -v      # expect: 242 tests, OK
```

Expected output, with nothing after `OK` — a stray line from any function that
prints during a test is a signal that output is leaking somewhere it should not:

```
Ran 242 tests in 0.1XXs

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
