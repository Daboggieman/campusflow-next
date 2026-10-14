import unittest

from campusflow.workflow import (
    assign_ticket,
    get_work_queue,
    move_ticket,
)
from campusflow.tickets import Ticket


def make_ticket(
    ticket_id="T001",
    priority="medium",
    status="open",
    assigned_to=None,
):
    return Ticket(
        id=ticket_id,
        title="Network issue",
        category="network",
        urgency="medium",
        affected_users=5,
        priority=priority,
        status=status,
        assigned_to=assigned_to,
    )


class TestMoveTicket(unittest.TestCase):

    def test_open_can_move_to_in_progress(self):
        ticket = make_ticket(status="open", assigned_to="Ada")
        move_ticket(ticket, "in_progress")
        self.assertEqual(ticket.status, "in_progress")

    def test_in_progress_can_move_to_resolved(self):
        ticket = make_ticket(status="in_progress", assigned_to="Ada")
        move_ticket(ticket, "resolved")
        self.assertEqual(ticket.status, "resolved")

    def test_resolved_can_be_reopened_to_open(self):
        ticket = make_ticket(status="resolved", assigned_to="Ada")
        move_ticket(ticket, "open")
        self.assertEqual(ticket.status, "open")

    def test_unknown_move_raises(self):
        ticket = make_ticket(status="open")
        with self.assertRaises(ValueError):
            move_ticket(ticket, "resolved")

    def test_in_progress_cannot_go_back_to_open(self):
        ticket = make_ticket(status="in_progress", assigned_to="Ada")
        with self.assertRaises(ValueError):
            move_ticket(ticket, "open")

    def test_open_cannot_move_to_unknown_status(self):
        ticket = make_ticket(status="open")
        with self.assertRaises(ValueError):
            move_ticket(ticket, "banana")

    def test_unassigned_cannot_move_to_in_progress(self):
        ticket = make_ticket(status="open", assigned_to=False)
        with self.assertRaises(ValueError):
            move_ticket(ticket, "in_progress")

    def test_move_failure_leaves_status_unchanged(self):
        ticket = make_ticket(status="open")
        with self.assertRaises(ValueError):
            move_ticket(ticket, "resolved")
        self.assertEqual(ticket.status, "open")


class TestAssignTicket(unittest.TestCase):

    def test_directly_assigns_the_staff_member(self):
        ticket = make_ticket(status="open")
        assign_ticket(ticket, "Rachel")
        self.assertEqual(ticket.assigned_to, "Rachel")

    def test_cannot_assign_resolved_ticket(self):
        ticket = make_ticket(status="resolved")
        with self.assertRaises(ValueError):
            assign_ticket(ticket, "Rachel")
        self.assertFalse(ticket.assigned_to)


class TestGetWorkQueue(unittest.TestCase):

    def test_includes_open_and_in_progress_only(self):
        tickets = {
            "T001": make_ticket("T001", priority="high", status="open"),
            "T002": make_ticket("T002", priority="low", status="in_progress"),
            "T003": make_ticket("T003", priority="medium", status="resolved"),
        }
        result = get_work_queue(tickets)
        self.assertIn(tickets["T001"], result)
        self.assertIn(tickets["T002"], result)
        self.assertNotIn(tickets["T003"], result)

    def test_sorts_by_priority_rank(self):
        cards = {
            "T001": make_ticket("T001", priority="high", status="open"),
            "T002": make_ticket("T002", priority="medium", status="in_progress"),
            "T003": make_ticket("T003", priority="low", status="open"),
            "T004": make_ticket("T004", priority="critical", status="in_progress"),
        }
        result = get_work_queue(cards)
        self.assertEqual(
            [ticket.id for ticket in result],
            ["T004", "T001", "T002", "T003"],
        )

    def test_sorts_by_numeric_ticket_number(self):
        tickets = {
            "T100": make_ticket("T100", priority="low", status="open"),
            "T020": make_ticket("T020", priority="low", status="open"),
            "T003": make_ticket("T003", priority="low", status="open"),
        }
        result = get_work_queue(tickets)
        self.assertEqual(
            [ticket.id for ticket in result],
            ["T003", "T020", "T100"],
        )


if __name__ == "__main__":
    unittest.main()
