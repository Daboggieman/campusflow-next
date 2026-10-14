import unittest

from campusflow.tickets import (
    Ticket,
    check_affected_users,
    check_category,
    check_title,
    check_urgency,
)


class TestCheckFunctions(unittest.TestCase):
    """Tests for the four field checks in tickets.py."""

    # --- title ---

    def test_check_title_returns_stripped(self):
        self.assertEqual(check_title("  Campus wifi  "), "campus wifi")

    def test_check_title_rejects_blank(self):
        with self.assertRaises(ValueError):
            check_title("   ")

    def test_check_title_rejects_empty(self):
        with self.assertRaises(ValueError):
            check_title("")

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

    # --- affected users ---

    def test_check_affected_users_parses_positive(self):
        self.assertEqual(check_affected_users("7"), 7)

    def test_check_affected_users_rejects_zero(self):
        with self.assertRaises(ValueError):
            check_affected_users("0")

    def test_check_affected_users_rejects_negative(self):
        with self.assertRaises(ValueError):
            check_affected_users("-3")

    def test_check_affected_users_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            check_affected_users("many")


class TestTicket(unittest.TestCase):
    """Tests for the Ticket dataclass."""

    def test_ticket_builds_with_normalised_fields(self):
        ticket = Ticket(
            id="T001",
            title="Campus wifi",
            category="NETWORK",
            urgency="High",
            affected_users=15,
            priority="critical",
            status="open",
            assigned_to=False,
        )
        self.assertEqual(ticket.title, "campus wifi")
        self.assertEqual(ticket.category, "network")
        self.assertEqual(ticket.urgency, "high")
        self.assertEqual(ticket.affected_users, 15)

    def test_bad_title_prevents_ticket_creation(self):
        with self.assertRaises(ValueError):
            Ticket(
                id="T001",
                title="   ",
                category="network",
                urgency="high",
                affected_users=5,
                priority="high",
                status="open",
                assigned_to=False,
            )

    def test_bad_affected_users_prevents_ticket_creation(self):
        with self.assertRaises(ValueError):
            Ticket(
                id="T001",
                title="Campus wifi",
                category="network",
                urgency="high",
                affected_users=0,
                priority="high",
                status="open",
                assigned_to=False,
            )


if __name__ == "__main__":
    unittest.main()
