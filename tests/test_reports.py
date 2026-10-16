"""Quality insights.

Engineer B — Search, Reporting and CLI Engineer.
Covers milestones B3: report totals are accurate, an empty dataset reports 0%
rather than crashing, and a reopened ticket is counted by its current status.

Note the deliberate split: the numbers are asserted against
``generate_report``'s dictionary, and only the display is asserted by capturing
stdout.
"""

import unittest
from contextlib import redirect_stdout
from io import StringIO

from campusflow.reports import generate_report, print_report
from support import make_ticket


def make_ticket_with_id(ticket_id="T1", priority="medium", status="open"):
    """Kept for the original tests, which pin priority independently."""
    return make_ticket(
        ticket_id,
        title="Network issue",
        category="network",
        urgency="medium",
        affected_users=5,
        priority=priority,
        status=status,
    )


class TestGenerateReport(unittest.TestCase):
    def test_empty_tickets_gives_zero_counts(self):
        report = generate_report({})
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["by_status"], {})
        self.assertEqual(report["by_priority"], {})

    def test_totals_by_status_and_priority(self):
        tickets = {
            "T001": make_ticket_with_id("T001", "high", "open"),
            "T002": make_ticket_with_id("T002", "medium", "in_progress"),
            "T003": make_ticket_with_id("T003", "low", "resolved"),
            "T004": make_ticket_with_id("T004", "critical", "open"),
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


class TestEmptyReport(unittest.TestCase):
    def test_resolution_percentage_is_zero_not_a_crash(self):
        """Bug-hunter test BH-2 — see docs/bug-hunter-tests.md.

        ``resolved / total * 100`` raises ZeroDivisionError when there are no
        tickets. An empty queue is the normal state of a fresh install, so the
        report has to answer 0% rather than fall over.
        """
        report = generate_report({})
        self.assertEqual(report["resolution_percentage"], 0.0)
        self.assertEqual(report["unresolved"], 0)
        self.assertEqual(report["resolved"], 0)
        self.assertEqual(report["by_category"], {})

    def test_printing_an_empty_report_says_so_and_shows_zero(self):
        buf = StringIO()
        with redirect_stdout(buf):
            print_report(generate_report({}))
        output = buf.getvalue()
        self.assertIn("No tickets yet.", output)
        self.assertIn("0.0%", output)


class TestUnresolvedAndResolvedCounts(unittest.TestCase):
    def test_unresolved_is_open_plus_in_progress(self):
        tickets = {
            "T1": make_ticket("T1", status="open"),
            "T2": make_ticket("T2", status="in_progress", assigned_to="Mentor A"),
            "T3": make_ticket("T3", status="resolved"),
        }
        report = generate_report(tickets)
        self.assertEqual(report["unresolved"], 2)
        self.assertEqual(report["resolved"], 1)

    def test_status_counts_add_up_to_the_total(self):
        """A ticket must not be counted under two statuses at once."""
        tickets = {
            "T1": make_ticket("T1", status="open"),
            "T2": make_ticket("T2", status="in_progress", assigned_to="Mentor A"),
            "T3": make_ticket("T3", status="resolved"),
            "T4": make_ticket("T4", status="open"),
        }
        report = generate_report(tickets)
        self.assertEqual(sum(report["by_status"].values()), report["total"])
        self.assertEqual(report["unresolved"] + report["resolved"], report["total"])

    def test_a_reopened_ticket_counts_as_open(self):
        """Counting must follow the CURRENT status, not the history."""
        ticket = make_ticket("T1", status="resolved")
        resolved_report = generate_report({"T1": ticket})
        self.assertEqual(resolved_report["resolved"], 1)
        self.assertEqual(resolved_report["resolution_percentage"], 100.0)

        ticket.status = "open"
        reopened_report = generate_report({"T1": ticket})
        self.assertEqual(reopened_report["resolved"], 0)
        self.assertEqual(reopened_report["unresolved"], 1)
        self.assertEqual(reopened_report["resolution_percentage"], 0.0)

    def test_resolution_percentage_is_rounded_to_one_decimal(self):
        tickets = {
            "T1": make_ticket("T1", status="resolved"),
            "T2": make_ticket("T2", status="open"),
            "T3": make_ticket("T3", status="open"),
        }
        self.assertEqual(generate_report(tickets)["resolution_percentage"], 33.3)


class TestCategoryCounts(unittest.TestCase):
    def test_counts_tickets_by_category(self):
        tickets = {
            "T1": make_ticket("T1", category="network"),
            "T2": make_ticket("T2", category="network"),
            "T3": make_ticket("T3", category="hardware"),
        }
        report = generate_report(tickets)
        self.assertEqual(report["by_category"]["network"], 2)
        self.assertEqual(report["by_category"]["hardware"], 1)

    def test_category_counts_add_up_to_the_total(self):
        tickets = {
            "T1": make_ticket("T1", category="network"),
            "T2": make_ticket("T2", category="software"),
            "T3": make_ticket("T3", category="other"),
        }
        report = generate_report(tickets)
        self.assertEqual(sum(report["by_category"].values()), report["total"])


class TestPrintReport(unittest.TestCase):
    def test_empty_prints_no_tickets_yet(self):
        buf = StringIO()
        with redirect_stdout(buf):
            print_report(generate_report({}))
        self.assertIn("No tickets yet.", buf.getvalue())

    def test_nonempty_prints_totals(self):
        tickets = {
            "T001": make_ticket_with_id("T001", "high", "open"),
            "T002": make_ticket_with_id("T002", "medium", "resolved"),
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

    def test_nonempty_prints_category_and_resolution_sections(self):
        tickets = {"T1": make_ticket("T1", category="network", status="resolved")}
        buf = StringIO()
        with redirect_stdout(buf):
            print_report(generate_report(tickets))
        out = buf.getvalue()
        self.assertIn("Tickets by category:", out)
        self.assertIn("network: 1", out)
        self.assertIn("resolution: 100.0%", out)


if __name__ == "__main__":
    unittest.main()
