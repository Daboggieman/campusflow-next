"""Read-only search and combined filtering.

Engineer B — Search, Reporting and CLI Engineer.
Covers milestones B1 and B2: case-insensitive substring search on the title,
and category/status/priority filters that combine with AND.
"""

import unittest

from campusflow.search import (
    describe_filters,
    search_tickets,
    sort_by_priority_then_id,
)
from support import make_ticket


def sample():
    """A small collection with one attribute varied at a time.

    Priorities are derived, so the collection stays loadable as well as
    searchable.
    """
    return {
        "T1": make_ticket("T1", title="Wi-Fi down in the library",
                          category="network", urgency="high", affected_users=12),
        "T2": make_ticket("T2", title="Wi-Fi drops in Hostel B",
                          category="network", urgency="low", affected_users=2,
                          status="in_progress", assigned_to="Mentor A"),
        "T3": make_ticket("T3", title="Projector will not power on",
                          category="hardware", urgency="low", affected_users=1,
                          status="resolved"),
        "T4": make_ticket("T4", title="Compiler missing from lab image",
                          category="software", urgency="medium", affected_users=4),
    }


class TestTitleSearch(unittest.TestCase):
    def test_matches_a_substring_with_different_case(self):
        found = search_tickets(sample(), title="wi-fi")
        self.assertEqual([ticket.id for ticket in found], ["T1", "T2"])

    def test_does_not_fuzzy_match_across_punctuation(self):
        """Substring matching only — "wifi" does not find "Wi-Fi".

        The brief rules out promising spelling correction, so a query that
        differs from the stored text by a hyphen is genuinely a miss. The
        case difference is what search *does* forgive.
        """
        self.assertEqual(search_tickets(sample(), title="wifi"), [])

    def test_ignores_case_in_both_directions(self):
        for query in ("WI-FI", "Wi-Fi", "wi-fi", "wI-fI"):
            self.assertEqual(
                [ticket.id for ticket in search_tickets(sample(), title=query)],
                ["T1", "T2"],
                msg=f"query {query!r}",
            )

    def test_matches_a_substring_anywhere_in_the_title(self):
        found = search_tickets(sample(), title="library")
        self.assertEqual([ticket.id for ticket in found], ["T1"])

    def test_returns_nothing_when_the_substring_is_absent(self):
        self.assertEqual(search_tickets(sample(), title="printer"), [])

    def test_blank_title_does_not_filter(self):
        self.assertEqual(len(search_tickets(sample(), title="   ")), 4)


class TestCombinedFilters(unittest.TestCase):
    def test_every_supplied_filter_must_match(self):
        """The brief's example: 'wifi' + network + open."""
        found = search_tickets(
            sample(), title="wi-fi", category="network", status="open"
        )
        self.assertEqual([ticket.id for ticket in found], ["T1"])

    def test_filters_are_and_not_or(self):
        """T1 is network+open and T3 is hardware+resolved; nothing is both."""
        found = search_tickets(sample(), category="network", status="resolved")
        self.assertEqual(found, [])

    def test_an_unsatisfiable_combination_is_empty(self):
        found = search_tickets(sample(), category="hardware", priority="critical")
        self.assertEqual(found, [])

    def test_a_single_filter_still_works(self):
        self.assertEqual(
            [ticket.id for ticket in search_tickets(sample(), status="resolved")],
            ["T3"],
        )

    def test_filters_accept_a_different_case(self):
        found = search_tickets(sample(), category="NETWORK", status="Open")
        self.assertEqual([ticket.id for ticket in found], ["T1"])

    def test_no_filters_returns_everything(self):
        self.assertEqual(len(search_tickets(sample())), 4)

    def test_an_empty_collection_returns_empty(self):
        self.assertEqual(search_tickets({}, title="anything"), [])


class TestSearchOrdering(unittest.TestCase):
    def test_results_are_ordered_by_ticket_number(self):
        tickets = {
            "T100": make_ticket("T100", title="third"),
            "T20": make_ticket("T20", title="second"),
            "T3": make_ticket("T3", title="first"),
        }
        found = search_tickets(tickets)
        self.assertEqual([ticket.id for ticket in found], ["T3", "T20", "T100"])

    def test_sort_by_priority_puts_critical_first(self):
        found = sort_by_priority_then_id(sample().values())
        self.assertEqual([ticket.id for ticket in found], ["T1", "T4", "T2", "T3"])

    def test_sort_by_priority_breaks_ties_on_ticket_number(self):
        tickets = [
            make_ticket("T30", urgency="high", affected_users=12),
            make_ticket("T4", urgency="high", affected_users=12),
        ]
        found = sort_by_priority_then_id(tickets)
        self.assertEqual([ticket.id for ticket in found], ["T4", "T30"])


class TestSearchIsReadOnly(unittest.TestCase):
    def test_searching_does_not_change_any_ticket(self):
        """Search is a view. If it mutated, a lookup could corrupt records."""
        tickets = sample()
        before = {
            ticket_id: (ticket.status, ticket.title, tuple(ticket.notes))
            for ticket_id, ticket in tickets.items()
        }

        search_tickets(tickets, title="wi-fi", category="network")
        sort_by_priority_then_id(tickets.values())
        search_tickets(tickets)

        after = {
            ticket_id: (ticket.status, ticket.title, tuple(ticket.notes))
            for ticket_id, ticket in tickets.items()
        }
        self.assertEqual(before, after)

    def test_returned_list_is_a_new_list(self):
        tickets = sample()
        found = search_tickets(tickets)
        found.clear()
        self.assertEqual(len(tickets), 4)


class TestDescribeFilters(unittest.TestCase):
    def test_describes_an_unfiltered_search(self):
        self.assertEqual(describe_filters(), "no filters (all tickets)")

    def test_describes_the_applied_filters(self):
        described = describe_filters("wi-fi", "network", "open", None)
        self.assertEqual(
            described, "title contains 'wi-fi' and category is network and status is open"
        )


if __name__ == "__main__":
    unittest.main()
