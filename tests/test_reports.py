import unittest
from io import StringIO
from contextlib import redirect_stdout

from campusflow.reports import generate_report, print_report
from campusflow.tickets import Ticket


def make_ticket(
    ticket_id="T001",
    priority="medium",
    status="open",
):
    return Ticket(
        id=ticket_id,
        title="Network issue",
        category="network",
        urgency="medium",
        affected_users=5,
        priority=priority,
        status=status,
        assigned_to=False,
    )


class TestGenerateReport(unittest.TestCase):

    def test_empty_tickets_gives_zero_counts(self):
        report = generate_report({})
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["by_status"], {})
        self.assertEqual(report["by_priority"], {})

    def test_totals_by_status_and_priority(self):
        tickets = {
            "T001": make_ticket("T001", "high", "open"),
            "T002": make_ticket("T002", "medium", "in_progress"),
            "T003": make_ticket("T003", "low", "resolved"),
            "T004": make_ticket("T004", "critical", "open"),
        }
        report = generate_report(tickets)
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["by_status"]["open"], 2)
        self.assertEqual(report["by_status"]["in_progress"], 1)
        self.assertEqual(report["by_status"]["resolved"], 1)
        self.assertEqual(report["by_priority"]["critical"], 1)
        self.assertEqual(report["by_priority"]["high"], 1)
        self.assertEqual(report["by_priority"]["medium"], 1)
        self.assertEqual(report["by_priority"]["low"], 1)


class TestPrintReport(unittest.TestCase):

    def test_empty_prints_no_tickets_yet(self):
        buf = StringIO()
        with redirect_stdout(buf):
            print_report(generate_report({}))
        self.assertIn("No tickets yet.", buf.getvalue())

    def test_nonempty_prints_totals(self):
        tickets = {
            "T001": make_ticket("T001", "high", "open"),
            "T002": make_ticket("T002", "medium", "resolved"),
        }
        buf = StringIO()
        with redirect_stdout(buf):
            print_report(generate_report(tickets))
        out = buf.getvalue()
        self.assertIn("Total tickets: 2", out)
        self.assertIn("open: 1", out)
        self.assertIn("resolved: 1", out)
        self.assertIn("high: 1", out)
        self.assertIn("medium: 1", out)


if __name__ == "__main__":
    unittest.main()
