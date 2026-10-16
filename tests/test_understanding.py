"""The Engineering Understanding Check.

Engineer B — Search, Reporting and CLI Engineer.
Covers milestone B5: the question bank is data, the scoring is logic, and the
two are never mixed. Also covers acceptance case 14 — an invalid answer is
rejected and the score reflects the submitted answers.
"""

import tempfile
import unittest
from pathlib import Path

from campusflow.understanding_check import (
    CHOICES,
    MIN_EXPLANATIONS,
    QUESTIONS,
    format_session,
    grade_answers,
    normalise_choice,
    run_check,
    score_answers,
)


def scripted_inputs(replies):
    """An ``input`` stand-in that hands back a fixed list of replies."""
    pending = iter(replies)

    def fake_input(_prompt=""):
        return next(pending)

    return fake_input


def collecting_print():
    lines = []
    return lines, lines.append


ALL_CORRECT = [question["answer"] for question in QUESTIONS]
ALL_WRONG = ["A" if question["answer"] != "A" else "B" for question in QUESTIONS]


class TestQuestionBank(unittest.TestCase):
    def test_there_are_six_questions(self):
        self.assertEqual(len(QUESTIONS), 6)

    def test_each_question_has_four_options_and_a_valid_answer(self):
        for question in QUESTIONS:
            self.assertEqual(sorted(question["options"]), list(CHOICES))
            self.assertIn(question["answer"], CHOICES)
            self.assertTrue(question["prompt"].strip())
            self.assertTrue(question["reference"].strip())

    def test_question_ids_are_unique(self):
        ids = [question["id"] for question in QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_bank_contains_no_scoring_logic(self):
        """The bank is data: no callables, so it cannot disagree with scoring."""
        for question in QUESTIONS:
            for value in question.values():
                self.assertNotIsInstance(value, type(lambda: None))


class TestNormaliseChoice(unittest.TestCase):
    def test_accepts_lowercase_and_padding(self):
        self.assertEqual(normalise_choice(" b "), "B")

    def test_rejects_anything_else(self):
        for bad in ("E", "", "BB", "1", None, 7):
            self.assertIsNone(normalise_choice(bad))


class TestScoring(unittest.TestCase):
    def test_all_correct_scores_six(self):
        self.assertEqual(score_answers(ALL_CORRECT), 6)

    def test_all_wrong_scores_zero(self):
        self.assertEqual(score_answers(ALL_WRONG), 0)

    def test_partial_credit(self):
        answers = list(ALL_WRONG)
        answers[0] = QUESTIONS[0]["answer"]
        answers[3] = QUESTIONS[3]["answer"]
        self.assertEqual(score_answers(answers), 2)

    def test_a_short_answer_list_scores_what_it_can(self):
        """Missing answers score nothing rather than raising."""
        self.assertEqual(score_answers([], QUESTIONS), 0)
        self.assertEqual(score_answers(["B"], QUESTIONS), 1)

    def test_scoring_is_never_negative_or_above_the_bank_size(self):
        self.assertEqual(score_answers(["Z"] * 20, QUESTIONS), 0)
        self.assertLessEqual(score_answers(ALL_CORRECT * 3, QUESTIONS), len(QUESTIONS))

    def test_grading_reports_each_question(self):
        graded = grade_answers(ALL_CORRECT)
        self.assertEqual(len(graded), 6)
        self.assertTrue(all(item["correct"] for item in graded))
        self.assertEqual(graded[0]["expected"], QUESTIONS[0]["answer"])


class TestRunCheck(unittest.TestCase):
    def test_scores_the_submitted_answers(self):
        lines, printer = collecting_print()
        replies = list(ALL_CORRECT) + ["Q1,Q4", "Because of the invariant", "Because AND"]
        result = run_check(
            input_fn=scripted_inputs(replies), print_fn=printer, save_path=None
        )
        self.assertEqual(result["score"], 6)
        self.assertEqual(result["total"], 6)
        self.assertIn("Score: 6/6", "\n".join(lines))

    def test_an_invalid_choice_is_rejected_and_re_asked(self):
        lines, printer = collecting_print()
        replies = ["X", "banana", *ALL_CORRECT, "Q1,Q2", "one", "two"]
        result = run_check(
            input_fn=scripted_inputs(replies), print_fn=printer, save_path=None
        )
        self.assertEqual(result["score"], 6)
        self.assertEqual(
            "\n".join(lines).count("invalid choice. Please enter A, B, C or D."), 2
        )
        self.assertEqual(result["answers"], ALL_CORRECT)

    def test_the_score_reflects_the_answers_not_the_retries(self):
        lines, printer = collecting_print()
        replies = ["E", *ALL_WRONG, "Q1,Q2", "reason", "reason"]
        result = run_check(
            input_fn=scripted_inputs(replies), print_fn=printer, save_path=None
        )
        self.assertEqual(result["score"], 0)

    def test_too_few_questions_chosen_for_explanation_is_re_asked(self):
        lines, printer = collecting_print()
        replies = [
            *ALL_CORRECT,
            "Q1",                 # only one — rejected
            "Q8,Q9",              # not in the bank — rejected
            "Q2,Q3",              # accepted
            "because of notes", "because of AND",
        ]
        result = run_check(
            input_fn=scripted_inputs(replies), print_fn=printer, save_path=None
        )
        self.assertEqual(sorted(result["explanations"]), ["Q2", "Q3"])
        self.assertGreaterEqual(
            "\n".join(lines).count("Please name at least"), 2
        )

    def test_explanations_are_recorded_verbatim_and_never_graded(self):
        """No keyword matching: the text is kept as written."""
        lines, printer = collecting_print()
        explanation = "I am not sure but I think B"
        replies = [*ALL_WRONG, "Q1,Q2", explanation, explanation]

        with_explanations = run_check(
            input_fn=scripted_inputs(replies), print_fn=printer, save_path=None
        )
        self.assertEqual(with_explanations["explanations"]["Q1"], explanation)

        # The same wrong answers with different prose score identically.
        probes = run_check(
            input_fn=scripted_inputs([*ALL_WRONG, "Q1,Q2", "wrong", "wrong"]),
            print_fn=printer,
            save_path=None,
        )
        self.assertEqual(with_explanations["score"], probes["score"])

    def test_requires_exactly_the_documented_minimum(self):
        self.assertEqual(MIN_EXPLANATIONS, 2)


class TestSessionNote(unittest.TestCase):
    def test_format_session_includes_the_score_and_explanations(self):
        result = run_check(
            input_fn=scripted_inputs([*ALL_CORRECT, "Q1,Q6", "why one", "why six"]),
            print_fn=collecting_print()[1],
            save_path=None,
        )
        text = format_session(result)
        self.assertIn("Score: 6/6", text)
        self.assertIn("why one", text)
        self.assertIn("Q6", text)

    def test_a_session_is_appended_to_the_learning_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "understanding-notes.md"
            run_check(
                input_fn=scripted_inputs([*ALL_CORRECT, "Q1,Q2", "first", "second"]),
                print_fn=collecting_print()[1],
                save_path=path,
            )
            run_check(
                input_fn=scripted_inputs([*ALL_WRONG, "Q1,Q2", "third", "fourth"]),
                print_fn=collecting_print()[1],
                save_path=path,
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("Score: 6/6", text)
            self.assertIn("Score: 0/6", text)
            self.assertEqual(text.count("# Engineering Understanding Check"), 2)


if __name__ == "__main__":
    unittest.main()
