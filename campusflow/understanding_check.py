"""The Engineering Understanding Check.

Three things are deliberately kept apart so each can be tested on its own:

1. :data:`QUESTIONS` — the question bank. Plain data. Changing a question is an
   edit here and nothing else.
2. :func:`score_answers` — the scoring. A pure function of the answers and the
   bank. It contains no ``input()``, no ``print()`` and no copy of the correct
   answers, so it cannot disagree with the bank.
3. :func:`run_check` — the conversation. It reads choices, rejects anything
   that is not A/B/C/D, and collects the written explanations.

Explanations are recorded **verbatim and never graded**. Marking free text
correct because it contains a keyword would be a guess dressed up as a mark,
and the brief rules it out explicitly; the written answers exist so a mentor
can read the learner's reasoning.
"""

from __future__ import annotations

from pathlib import Path

CHOICES = ("A", "B", "C", "D")

MIN_EXPLANATIONS = 2

#: Six scenario questions about this application's own behaviour.
QUESTIONS = [
    {
        "id": "Q1",
        "prompt": (
            "Ticket T1 is open and has no one assigned to it. A user tries to "
            "move it to in_progress. What should happen?"
        ),
        "options": {
            "A": "Accept the move, assigned or not",
            "B": "Reject the move and preserve all ticket data",
            "C": "Resolve the ticket automatically instead",
            "D": "Remove the ticket from the collection",
        },
        "answer": "B",
        "reference": (
            "campusflow/workflow.py move_ticket() raises before it writes, so "
            "the ticket is unchanged; an unassigned ticket cannot start work."
        ),
    },
    {
        "id": "Q2",
        "prompt": (
            "The application holds zero tickets. What should the resolution "
            "percentage show?"
        ),
        "options": {
            "A": "The application crashes",
            "B": "100%",
            "C": "0%",
            "D": "Divide by one and show no explanation",
        },
        "answer": "C",
        "reference": (
            "campusflow/reports.py generate_report() guards with 'if total "
            "else 0.0', so an empty collection reports 0.0% with no division."
        ),
    },
    {
        "id": "Q3",
        "prompt": (
            "A search is run with title='wifi', category='Network' and "
            "status='open'. Which records should come back?"
        ),
        "options": {
            "A": "Any record matching at least one of the filters",
            "B": "Only records matching all the supplied filters",
            "C": "Every network record, whatever its status",
            "D": "Every open record, whatever its category",
        },
        "answer": "B",
        "reference": (
            "campusflow/search.py applies the filters with 'continue' guards, "
            "so a record must survive every supplied filter: AND, not OR."
        ),
    },
    {
        "id": "Q4",
        "prompt": (
            "A resolved ticket is given the 'Add follow-up note' action. What "
            "should happen?"
        ),
        "options": {
            "A": "Append the note anyway",
            "B": "Delete the ticket's earlier notes and start again",
            "C": "Reject the note until the ticket is reopened",
            "D": "Change the status quietly and then add the note",
        },
        "answer": "C",
        "reference": (
            "campusflow/notes.py add_note() refuses anything not open or "
            "in_progress. Reopening restores the earlier notes and the next "
            "note number continues from them."
        ),
    },
    {
        "id": "Q5",
        "prompt": (
            "The tickets file contains two entries with the same ticket ID. "
            "What should loading do?"
        ),
        "options": {
            "A": "Keep both entries",
            "B": "Replace the in-memory tickets with the duplicates",
            "C": "Reject the load and leave the current tickets untouched",
            "D": "Rename the duplicate IDs silently",
        },
        "answer": "C",
        "reference": (
            "campusflow/jsonio.py rejects a repeated key, and storage raises "
            "DataError before returning, so the caller keeps its own data."
        ),
    },
    {
        "id": "Q6",
        "prompt": (
            "A pull request changes ticket validation but adds no negative "
            "tests. What is the best review action?"
        ),
        "options": {
            "A": "Approve it, because the code runs without errors",
            "B": "Request focused tests for the rejected inputs, with reasoning",
            "C": "Merge it immediately to avoid blocking the author",
            "D": "Ask an AI tool to approve it on the reviewer's behalf",
        },
        "answer": "B",
        "reference": (
            "Validation is only demonstrated by the inputs it refuses. A "
            "'it runs' check never exercises the rejection paths."
        ),
    },
]


def normalise_choice(raw_choice):
    """Return a valid A/B/C/D choice, or ``None`` if the input is not one."""
    if not isinstance(raw_choice, str):
        return None
    choice = raw_choice.strip().upper()
    return choice if choice in CHOICES else None


def score_answers(answers, questions=None) -> int:
    """One point per correct answer. Never less than 0 or more than the bank.

    A short or over-long answer list is tolerated here so that a caller which
    collected the wrong number of answers gets a score it can reason about,
    rather than an exception. Missing answers simply score nothing.
    """
    bank = QUESTIONS if questions is None else questions
    return sum(
        1
        for question, answer in zip(bank, answers)
        if normalise_choice(answer) == question["answer"]
    )


def grade_answers(answers, questions=None) -> list:
    """Per-question detail, for feedback and for mentor discussion."""
    bank = QUESTIONS if questions is None else questions
    graded = []
    for index, question in enumerate(bank):
        given = answers[index] if index < len(answers) else None
        chosen = normalise_choice(given)
        graded.append(
            {
                "id": question["id"],
                "given": chosen,
                "expected": question["answer"],
                "correct": chosen == question["answer"],
                "reference": question["reference"],
            }
        )
    return graded


def _ask_choice(question, input_fn, print_fn):
    """Ask one question, re-prompting until the answer is A, B, C or D."""
    while True:
        print_fn("")
        print_fn(f"{question['id']}. {question['prompt']}")
        for letter in CHOICES:
            print_fn(f"  {letter}. {question['options'][letter]}")

        choice = normalise_choice(input_fn("Your answer (A/B/C/D): "))
        if choice is not None:
            return choice
        print_fn("Invalid choice. Please enter A, B, C or D.")


def _ask_for_ids(question_ids, input_fn, print_fn):
    """Collect at least :data:`MIN_EXPLANATIONS` valid question IDs to explain."""
    while True:
        raw = input_fn(
            f"Which answers will you explain? Enter at least "
            f"{MIN_EXPLANATIONS} IDs separated by commas (e.g. Q1,Q4): "
        )
        chosen = []
        for part in str(raw).replace(";", ",").split(","):
            candidate = part.strip().upper()
            if candidate in question_ids and candidate not in chosen:
                chosen.append(candidate)

        if len(chosen) >= MIN_EXPLANATIONS:
            return chosen
        print_fn(
            f"Please name at least {MIN_EXPLANATIONS} different questions from "
            f"this check: {', '.join(question_ids)}."
        )


def format_session(result) -> str:
    """A markdown record of one sitting, for the learning log."""
    lines = [
        "# Engineering Understanding Check",
        "",
        f"Score: {result['score']}/{result['total']}",
        "",
        "## Answers",
        "",
    ]
    for item in result["graded"]:
        mark = "correct" if item["correct"] else f"expected {item['expected']}"
        lines.append(f"- {item['id']}: answered {item['given']} — {mark}")

    lines.extend(["", "## Written explanations", ""])
    if result["explanations"]:
        for question_id, text in result["explanations"].items():
            lines.append(f"- **{question_id}**: {text}")
    else:
        lines.append("- (none recorded)")

    lines.append("")
    return "\n".join(lines)


def run_check(input_fn=input, print_fn=print, save_path=None) -> dict:
    """Run the whole check and return the session.

    ``input_fn`` and ``print_fn`` are injectable so the whole flow can be
    driven from a test without a person typing. When ``save_path`` is given the
    session is appended to that file as a learning note.
    """
    print_fn("=== Engineering Understanding Check ===")
    print_fn(
        "Six questions on how this application behaves. "
        "Answers are scored; written explanations are not."
    )

    answers = [_ask_choice(question, input_fn, print_fn) for question in QUESTIONS]
    graded = grade_answers(answers)
    score = score_answers(answers)

    print_fn("")
    print_fn("--- Feedback ---")
    for item in graded:
        if item["correct"]:
            print_fn(f"{item['id']}: correct.")
        else:
            print_fn(
                f"{item['id']}: you answered {item['given']}, "
                f"the answer is {item['expected']}. {item['reference']}"
            )

    print_fn("")
    print_fn(f"Score: {score}/{len(QUESTIONS)}")

    question_ids = [question["id"] for question in QUESTIONS]
    print_fn("")
    print_fn(
        f"Now explain at least {MIN_EXPLANATIONS} of your answers in your own "
        "words. These are not marked; they are for your mentor."
    )

    explanations = {}
    for question_id in _ask_for_ids(question_ids, input_fn, print_fn):
        explanations[question_id] = input_fn(f"Explain {question_id}: ").strip()

    result = {
        "answers": answers,
        "graded": graded,
        "score": score,
        "total": len(QUESTIONS),
        "explanations": explanations,
    }

    if save_path is not None:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(format_session(result) + "\n")
        print_fn(f"Session saved to {path}.")

    return result
