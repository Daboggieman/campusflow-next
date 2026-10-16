"""Field checks and the ``Ticket`` record.

Engineer A — Ticket Safety and Storage Engineer.
Covers milestones A1/A3: reject invalid ``affected_users``, invalid categories,
and keep a malformed record from ever becoming an object.
"""

import unittest

from campusflow.tickets import (
    Ticket,
    check_affected_users,
    check_assigned_to,
    check_category,
    check_priority,
    check_status,
    check_ticket_id,
    check_title,
    check_urgency,
    ticket_number,
)
from campusflow.errors import ValidationError


def build_ticket(**overrides):
    """A valid ticket, with named fields overridable one at a time."""
    fields = {
        "id": "T1",
        "title": "Campus wifi",
        "category": "network",
        "urgency": "high",
        "affected_users": 15,
        "priority": "critical",
        "status": "open",
        "assigned_to": None,
    }
    fields.update(overrides)
    return Ticket(**fields)


class TestCheckFunctions(unittest.TestCase):
    """Tests for the field checks in tickets.py."""

    # --- title ---

    def test_check_title_returns_stripped(self):
        self.assertEqual(check_title("  Campus wifi  "), "campus wifi")

    def test_check_title_rejects_blank(self):
        with self.assertRaises(ValueError):
            check_title("   ")

    def test_check_title_rejects_empty(self):
        with self.assertRaises(ValueError):
            check_title("")

    def test_check_title_rejects_non_text(self):
        with self.assertRaises(ValidationError):
            check_title(None)

    # --- category ---

    def test_check_category_returns_canonical_spelling(self):
        self.assertEqual(check_category("NETWORK"), "network")

    def test_check_category_rejects_unknown(self):
        with self.assertRaises(ValueError):
            check_category("billing")

    # --- urgency ---

    def test_check_urgency_returns_canonical_lowercase(self):
        self.assertEqual(check_urgency("High"), "high")

    def test_check_urgency_rejects_unknown(self):
        with self.assertRaises(ValueError):
            check_urgency("urgent")

    def test_check_urgency_no_longer_accepts_critical(self):
        """'critical' is a priority, not an urgency.

        The original ``urgencies`` list contained it, so the same word meant
        two different things depending on which list it was checked against.
        No shipped ticket and no test used it as an urgency.
        """
        with self.assertRaises(ValidationError):
            check_urgency("critical")

    # --- status and priority ---

    def test_check_status_accepts_the_three_legal_values(self):
        for status in ("open", "in_progress", "resolved"):
            self.assertEqual(check_status(status.upper()), status)

    def test_check_status_rejects_unknown(self):
        with self.assertRaises(ValidationError):
            check_status("banana")

    def test_check_priority_rejects_unknown(self):
        with self.assertRaises(ValidationError):
            check_priority("urgent")

    # --- affected users ---

    def test_check_affected_users_parses_positive(self):
        self.assertEqual(check_affected_users("7"), 7)

    def test_check_affected_users_accepts_a_plain_integer(self):
        self.assertEqual(check_affected_users(7), 7)

    def test_check_affected_users_rejects_zero(self):
        with self.assertRaises(ValueError):
            check_affected_users("0")

    def test_check_affected_users_rejects_negative(self):
        with self.assertRaises(ValueError):
            check_affected_users("-3")

    def test_check_affected_users_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            check_affected_users("many")

    def test_check_affected_users_rejects_boolean(self):
        """``isinstance(True, int)`` is true, so True used to become 1.

        This is the check the original version was missing: ``int(True) == 1``
        meant a JSON ``true`` counted as one affected user instead of being
        refused as the wrong type.
        """
        with self.assertRaises(ValidationError):
            check_affected_users(True)
        with self.assertRaises(ValidationError):
            check_affected_users(False)

    def test_check_affected_users_rejects_float(self):
        """A float used to be truncated, so 3.7 silently meant 3."""
        with self.assertRaises(ValidationError):
            check_affected_users(3.7)
        with self.assertRaises(ValidationError):
            check_affected_users(0.5)

    def test_check_affected_users_rejects_decimal_text(self):
        with self.assertRaises(ValidationError):
            check_affected_users("3.5")

    # --- ticket id ---

    def test_check_ticket_id_uppercases(self):
        self.assertEqual(check_ticket_id("t12"), "T12")

    def test_check_ticket_id_keeps_leading_zeros(self):
        self.assertEqual(check_ticket_id("T020"), "T020")

    def test_check_ticket_id_rejects_malformed(self):
        for bad in ("", "T", "12", "TT1", "T-1", "T0", None):
            with self.assertRaises(ValidationError):
                check_ticket_id(bad)

    def test_ticket_number_sorts_numerically(self):
        self.assertEqual(ticket_number("T020"), 20)
        self.assertLess(ticket_number("T20"), ticket_number("T100"))

    def test_ticket_number_rejects_malformed(self):
        with self.assertRaises(ValidationError):
            ticket_number("banana")

    # --- assignment ---

    def test_check_assigned_to_treats_false_as_unassigned(self):
        """The original wrote ``False`` for "nobody"; old files must still load."""
        self.assertIsNone(check_assigned_to(False))
        self.assertIsNone(check_assigned_to(None))
        self.assertIsNone(check_assigned_to("   "))

    def test_check_assigned_to_keeps_a_label(self):
        self.assertEqual(check_assigned_to("  Mr. Izzy "), "Mr. Izzy")

    def test_check_assigned_to_rejects_non_text(self):
        with self.assertRaises(ValidationError):
            check_assigned_to(7)


class TestTicket(unittest.TestCase):
    """Tests for the Ticket dataclass."""

    def test_ticket_builds_with_normalised_fields(self):
        ticket = build_ticket(category="NETWORK", urgency="High")
        self.assertEqual(ticket.title, "campus wifi")
        self.assertEqual(ticket.category, "network")
        self.assertEqual(ticket.urgency, "high")
        self.assertEqual(ticket.affected_users, 15)

    def test_bad_title_prevents_ticket_creation(self):
        with self.assertRaises(ValueError):
            build_ticket(title="   ")

    def test_bad_affected_users_prevents_ticket_creation(self):
        for bad in (0, -1, 1.5, True):
            with self.assertRaises(ValidationError):
                build_ticket(affected_users=bad)

    def test_bad_status_prevents_ticket_creation(self):
        """A hand-edited file could previously load status 'banana'."""
        with self.assertRaises(ValidationError):
            build_ticket(status="banana")

    def test_bad_priority_prevents_ticket_creation(self):
        with self.assertRaises(ValidationError):
            build_ticket(priority="very high")

    def test_bad_ticket_id_prevents_ticket_creation(self):
        with self.assertRaises(ValidationError):
            build_ticket(id="banana")

    def test_notes_default_to_an_empty_list(self):
        self.assertEqual(build_ticket().notes, [])

    def test_notes_are_validated_on_construction(self):
        with self.assertRaises(ValidationError):
            build_ticket(notes=[{"note_id": "X1", "author": "A", "message": "hello"}])

    def test_duplicate_note_ids_within_a_ticket_are_rejected(self):
        note = {"note_id": "N001", "author": "Mentor A", "message": "First note"}
        with self.assertRaises(ValidationError):
            build_ticket(notes=[note, dict(note)])

    def test_notes_are_not_shared_between_tickets(self):
        """A mutable default would leak one ticket's notes into every other."""
        first, second = build_ticket(), build_ticket(id="T2")
        first.notes.append(
            {"note_id": "N001", "author": "Mentor A", "message": "Only mine"}
        )
        self.assertEqual(second.notes, [])

    def test_unresolved_reflects_current_status(self):
        self.assertTrue(build_ticket(status="open").is_unresolved)
        self.assertTrue(build_ticket(status="in_progress").is_unresolved)
        self.assertFalse(build_ticket(status="resolved").is_unresolved)


if __name__ == "__main__":
    unittest.main()
