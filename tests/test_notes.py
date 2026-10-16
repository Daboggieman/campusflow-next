"""Structured follow-up notes.

Engineer A — Ticket Safety and Storage Engineer.
Covers milestone A4: add a note to an open ticket, refuse one on a resolved
ticket, and prove that a rejected action changes nothing — including the note
numbering.
"""

import unittest

from campusflow.errors import ValidationError
from campusflow.notes import add_note, get_notes, next_note_id, notes_allowed
from campusflow.tickets import check_note_author, check_note_message
from campusflow.workflow import move_ticket
from support import make_note, make_ticket


class TestNextNoteId(unittest.TestCase):
    def test_first_note_is_n001(self):
        self.assertEqual(next_note_id(make_ticket()), "N001")

    def test_continues_from_the_highest_existing(self):
        ticket = make_ticket(notes=[make_note("N001"), make_note("N002")])
        self.assertEqual(next_note_id(ticket), "N003")

    def test_a_gap_does_not_reuse_a_number(self):
        """Notes are N001 and N003; the next is N004, never N002 again."""
        ticket = make_ticket(notes=[make_note("N001"), make_note("N003")])
        self.assertEqual(next_note_id(ticket), "N004")

    def test_rolls_over_past_three_digits(self):
        ticket = make_ticket(notes=[make_note("N999")])
        self.assertEqual(next_note_id(ticket), "N1000")


class TestAddNote(unittest.TestCase):
    def test_adds_a_note_to_an_open_ticket(self):
        tickets = {"T1": make_ticket()}
        note_id = add_note(tickets, "T1", "Mentor A", "Wi-Fi router reboot attempted")
        self.assertEqual(note_id, "N001")
        self.assertEqual(tickets["T1"].notes[0]["note_id"], "N001")
        self.assertEqual(tickets["T1"].notes[0]["author"], "Mentor A")

    def test_numbers_notes_consecutively(self):
        tickets = {"T1": make_ticket()}
        add_note(tickets, "T1", "Mentor A", "Wi-Fi router reboot attempted")
        second = add_note(tickets, "T1", "Mentor B", "Investigating switch ports")
        self.assertEqual(second, "N002")

    def test_accepts_a_note_on_an_in_progress_ticket(self):
        ticket = make_ticket(status="in_progress", assigned_to="Mentor A")
        self.assertEqual(add_note({"T1": ticket}, "T1", "Mentor B", "Checked the port"), "N001")

    def test_accepts_a_lowercase_ticket_id(self):
        tickets = {"T1": make_ticket()}
        self.assertEqual(add_note(tickets, "t1", "Mentor A", "Router rebooted"), "N001")

    def test_trims_the_author_and_message(self):
        tickets = {"T1": make_ticket()}
        add_note(tickets, "T1", "  Mentor A  ", "   Router reboot attempted   ")
        self.assertEqual(tickets["T1"].notes[0]["author"], "Mentor A")
        self.assertEqual(tickets["T1"].notes[0]["message"], "Router reboot attempted")

    def test_accepts_a_message_of_exactly_the_minimum_length(self):
        tickets = {"T1": make_ticket()}
        self.assertEqual(add_note(tickets, "T1", "Mentor A", "12345"), "N001")

    def test_accepts_a_message_of_exactly_the_maximum_length(self):
        tickets = {"T1": make_ticket()}
        self.assertEqual(add_note(tickets, "T1", "Mentor A", "x" * 300), "N001")


class TestRejectedNotesChangeNothing(unittest.TestCase):
    """Every rejection must leave the ticket byte-for-byte identical."""

    def assert_unchanged(self, tickets, ticket_id, author, message, expected_message):
        before = list(tickets[ticket_id].notes)
        with self.assertRaises(ValidationError) as caught:
            add_note(tickets, ticket_id, author, message)
        self.assertIn(expected_message, str(caught.exception))
        self.assertEqual(tickets[ticket_id].notes, before)

    def test_a_resolved_ticket_refuses_a_note(self):
        tickets = {"T1": make_ticket(status="resolved")}
        self.assert_unchanged(
            tickets, "T1", "Mentor A", "Trying to add anyway", "reopen it first"
        )

    def test_a_rejected_note_does_not_consume_a_note_id(self):
        """The acceptance sequence from the brief.

        N001 and N002 exist, the ticket is resolved so N003 is refused, the
        ticket is reopened, and the next note must be N003 — not N004.
        """
        ticket = make_ticket(
            status="open",
            assigned_to="Mentor A",
            notes=[make_note("N001"), make_note("N002")],
        )
        tickets = {"T1": ticket}

        move_ticket(ticket, "in_progress")
        move_ticket(ticket, "resolved")

        with self.assertRaises(ValidationError):
            add_note(tickets, "T1", "Mentor C", "Note while resolved")

        self.assertEqual(len(ticket.notes), 2)

        move_ticket(ticket, "open")
        self.assertEqual(add_note(tickets, "T1", "Mentor C", "Now reopened"), "N003")

    def test_a_blank_author_is_refused(self):
        tickets = {"T1": make_ticket()}
        self.assert_unchanged(
            tickets, "T1", "   ", "A perfectly good message", "author cannot be blank"
        )

    def test_a_too_short_message_is_refused(self):
        tickets = {"T1": make_ticket()}
        self.assert_unchanged(tickets, "T1", "Mentor A", "hi", "at least")

    def test_a_message_of_only_spaces_is_refused(self):
        tickets = {"T1": make_ticket()}
        self.assert_unchanged(tickets, "T1", "Mentor A", "        ", "at least")

    def test_a_too_long_message_is_refused(self):
        tickets = {"T1": make_ticket()}
        self.assert_unchanged(tickets, "T1", "Mentor A", "x" * 301, "at most")

    def test_an_unknown_ticket_is_refused(self):
        tickets = {"T1": make_ticket()}
        with self.assertRaises(ValidationError) as caught:
            add_note(tickets, "T99", "Mentor A", "A perfectly good message")
        self.assertIn("not found", str(caught.exception))

    def test_a_malformed_ticket_id_is_refused(self):
        tickets = {"T1": make_ticket()}
        with self.assertRaises(ValidationError):
            add_note(tickets, "banana", "Mentor A", "A perfectly good message")

    def test_a_non_text_message_is_refused(self):
        tickets = {"T1": make_ticket()}
        self.assert_unchanged(tickets, "T1", "Mentor A", 12345, "must be text")


class TestNotesSurviveTheLifecycle(unittest.TestCase):
    def test_notes_are_preserved_through_resolve_and_reopen(self):
        ticket = make_ticket(status="open", assigned_to="Mentor A")
        tickets = {"T1": ticket}
        add_note(tickets, "T1", "Mentor A", "Wi-Fi router reboot attempted")

        move_ticket(ticket, "in_progress")
        move_ticket(ticket, "resolved")
        self.assertEqual(len(ticket.notes), 1)
        self.assertFalse(notes_allowed(ticket))

        move_ticket(ticket, "open")
        self.assertTrue(notes_allowed(ticket))
        self.assertEqual(len(ticket.notes), 1)


class TestGetNotes(unittest.TestCase):
    def test_returns_notes_in_id_order(self):
        ticket = make_ticket(notes=[make_note("N003"), make_note("N001"), make_note("N002")])
        ordered = [note["note_id"] for note in get_notes({"T1": ticket}, "T1")]
        self.assertEqual(ordered, ["N001", "N002", "N003"])

    def test_returns_an_empty_list_when_there_are_none(self):
        self.assertEqual(get_notes({"T1": make_ticket()}, "T1"), [])

    def test_unknown_ticket_is_refused(self):
        with self.assertRaises(ValidationError):
            get_notes({"T1": make_ticket()}, "T99")


class TestNoteFieldChecks(unittest.TestCase):
    def test_message_length_boundaries(self):
        self.assertEqual(check_note_message("12345"), "12345")
        with self.assertRaises(ValidationError):
            check_note_message("1234")

    def test_author_must_not_be_blank(self):
        with self.assertRaises(ValidationError):
            check_note_author("  ")
        self.assertEqual(check_note_author(" Mentor A "), "Mentor A")


if __name__ == "__main__":
    unittest.main()
