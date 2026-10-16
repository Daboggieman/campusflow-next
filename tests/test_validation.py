"""Central validation helpers, including the whole-collection load check.

Engineer A — Ticket Safety and Storage Engineer.
Covers milestones A3 and A5: invalid records are refused, and a collection is
accepted only when every record in it is valid.
"""

import unittest

from campusflow import categories
from campusflow.errors import DataError, ValidationError
from campusflow.validation import (
    validate_new_category,
    validate_search_filters,
    validate_ticket_collection,
    validate_ticket_record,
)


def record(**overrides):
    """A valid stored record, as it would arrive from JSON."""
    data = {
        "id": "T1",
        "title": "Campus wifi",
        "category": "network",
        "urgency": "high",
        "affected_users": 15,
        "priority": "critical",
        "status": "open",
        "assigned_to": None,
    }
    data.update(overrides)
    return data


class TestValidateNewCategory(unittest.TestCase):
    def setUp(self):
        categories.reset_categories()
        self.addCleanup(categories.reset_categories)

    def test_accepts_an_active_category(self):
        self.assertEqual(validate_new_category("Network"), "network")

    def test_rejects_an_unknown_category(self):
        with self.assertRaises(ValidationError):
            validate_new_category("billing")

    def test_rejects_a_retired_category(self):
        """Retiring stops a category being chosen for new work.

        Existing tickets keep it — that narrower rule is
        ``check_category``'s default, which accepts the known set.
        """
        categories.retire_category("administrative")
        with self.assertRaises(ValidationError):
            validate_new_category("administrative")


class TestValidateTicketRecord(unittest.TestCase):
    def test_accepts_a_valid_record(self):
        ticket = validate_ticket_record("T1", record())
        self.assertEqual(ticket.id, "T1")
        self.assertEqual(ticket.affected_users, 15)

    def test_accepts_a_record_without_notes(self):
        """A file written before CampusFlow Next has no notes key."""
        self.assertEqual(validate_ticket_record("T1", record()).notes, [])

    def test_accepts_a_record_with_notes(self):
        ticket = validate_ticket_record(
            "T1",
            record(notes=[{"note_id": "N001", "author": "Mentor A", "message": "Rebooted router"}]),
        )
        self.assertEqual(len(ticket.notes), 1)

    def test_rejects_a_key_that_disagrees_with_the_stored_id(self):
        with self.assertRaises(DataError) as caught:
            validate_ticket_record("T2", record())
        self.assertIn("does not match", str(caught.exception))

    def test_rejects_a_missing_field(self):
        incomplete = record()
        del incomplete["category"]
        with self.assertRaises(DataError) as caught:
            validate_ticket_record("T1", incomplete)
        self.assertIn("missing required field", str(caught.exception))

    def test_rejects_an_unexpected_field(self):
        with self.assertRaises(DataError) as caught:
            validate_ticket_record("T1", record(secret_note="oops"))
        self.assertIn("unexpected field", str(caught.exception))

    def test_rejects_a_record_that_is_not_an_object(self):
        with self.assertRaises(DataError):
            validate_ticket_record("T1", "just a string")

    def test_rejects_a_priority_that_contradicts_the_rules(self):
        """urgency 'high' with 15 users implies 'critical', not 'low'."""
        with self.assertRaises(DataError) as caught:
            validate_ticket_record("T1", record(priority="low"))
        self.assertIn("implies 'critical'", str(caught.exception))

    def test_rejects_an_invalid_status(self):
        with self.assertRaises(DataError):
            validate_ticket_record("T1", record(status="banana"))

    def test_rejects_an_unknown_category(self):
        with self.assertRaises(DataError):
            validate_ticket_record("T1", record(category="billing"))

    def test_accepts_a_retired_category(self):
        """The whole point of the active/retired split: no data is orphaned."""
        categories.reset_categories()
        self.addCleanup(categories.reset_categories)
        categories.retire_category("administrative")
        ticket = validate_ticket_record(
            "T1",
            record(category="administrative", urgency="low", affected_users=1, priority="low"),
        )
        self.assertEqual(ticket.category, "administrative")


class TestValidateTicketCollection(unittest.TestCase):
    def test_accepts_an_empty_collection(self):
        self.assertEqual(validate_ticket_collection({}), {})

    def test_accepts_a_consistent_collection(self):
        tickets = validate_ticket_collection(
            {"T1": record(), "T2": record(id="T2", urgency="low", affected_users=1, priority="low")}
        )
        self.assertEqual(sorted(tickets), ["T1", "T2"])

    def test_rejects_a_non_object(self):
        with self.assertRaises(DataError):
            validate_ticket_collection([record()])

    def test_one_bad_record_rejects_the_whole_collection(self):
        """No partial result: the caller must be able to keep its old data."""
        good = record(id="T9", urgency="low", affected_users=1, priority="low")
        bad = record(id="T2", urgency="medium", affected_users=1, priority="low")
        with self.assertRaises(DataError):
            validate_ticket_collection({"T9": good, "T2": bad})


class TestValidateSearchFilters(unittest.TestCase):
    def test_blank_filters_mean_do_not_filter(self):
        self.assertEqual(
            validate_search_filters(category="", status="   ", priority=None),
            {"category": None, "status": None, "priority": None},
        )

    def test_normalises_supplied_filters(self):
        self.assertEqual(
            validate_search_filters(category="NETWORK", status="Open", priority="High"),
            {"category": "network", "status": "open", "priority": "high"},
        )

    def test_rejects_an_unknown_option(self):
        with self.assertRaises(ValidationError) as caught:
            validate_search_filters(status="closed")
        self.assertIn("status filter", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
