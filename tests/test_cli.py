"""The CLI: input loops, retries, and friendly failure messages.

Engineer B — Search, Reporting and CLI Engineer.
Covers milestone B4 and B6: the note menu uses Engineer A's functions and
reports failures helpfully, and invalid CLI choices re-prompt instead of
crashing.

``main.ask`` is the single point where the program reads the keyboard, so
patching it drives the whole menu from a test without a person typing.
"""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

import main
from support import TemporaryDataDirTestCase, make_ticket


class CliTestCase(TemporaryDataDirTestCase):
    def setUp(self):
        super().setUp()
        main.state = main.AppState()
        self.addCleanup(setattr, main, "state", main.AppState())

    def run_with_input(self, replies, action):
        """Call ``action`` with scripted keystrokes; return (result, printed)."""
        buf = StringIO()
        with mock.patch.object(main, "ask", side_effect=list(replies)):
            with redirect_stdout(buf):
                result = action()
        return result, buf.getvalue()


class TestMenuShape(CliTestCase):
    def test_every_entry_is_a_label_and_an_action(self):
        for entry in main.menu:
            self.assertEqual(len(entry), 2)
            self.assertIsInstance(entry[0], str)
            self.assertTrue(callable(entry[1]))

    def test_quit_is_the_last_entry(self):
        self.assertIs(main.menu[-1][1], main.quit_program)

    def test_the_required_actions_are_present(self):
        labels = [label for label, _ in main.menu]
        for required in (
            "create ticket",
            "assign ticket",
            "change status",
            "open work queue",
            "add follow-up note",
            "view ticket notes",
            "search tickets",
            "reports",
            "engineering understanding check",
        ):
            self.assertIn(required, labels)

    def test_labels_are_unique(self):
        labels = [label for label, _ in main.menu]
        self.assertEqual(len(labels), len(set(labels)))


class TestInputLoops(CliTestCase):
    def test_ask_validated_re_asks_after_a_bad_answer(self):
        _, printed = self.run_with_input(
            ["", "   ", "Wi-Fi down"],
            lambda: main.ask_validated("title: ", main.check_title),
        )
        self.assertEqual(printed.count("Title cannot be blank."), 2)

    def test_ask_validated_returns_the_cleaned_value(self):
        value, _ = self.run_with_input(
            ["NETWORK"], lambda: main.ask_validated("c: ", main.check_category)
        )
        self.assertEqual(value, "network")

    def test_a_blank_search_filter_means_do_not_filter(self):
        value, _ = self.run_with_input([""], lambda: main.ask_filter("s: ", main.STATUSES, "status"))
        self.assertIsNone(value)

    def test_an_invalid_search_filter_re_prompts(self):
        value, printed = self.run_with_input(
            ["closed", "open"],
            lambda: main.ask_filter("s: ", main.STATUSES, "status"),
        )
        self.assertEqual(value, "open")
        self.assertIn("Choose one of: open, in_progress, resolved", printed)

    def test_ask_ticket_id_reports_an_unknown_ticket(self):
        main.state.tickets = {"T1": make_ticket("T1")}
        value, printed = self.run_with_input(
            ["T99", "T1"], lambda: main.ask_ticket_id("id: ")
        )
        self.assertEqual(value, "T1")
        self.assertIn("Ticket T99 not found.", printed)


class TestCreateTicket(CliTestCase):
    def test_creates_a_ticket_with_a_derived_priority(self):
        _, printed = self.run_with_input(
            ["Wi-Fi down in the library", "network", "high", "12"], main.create_ticket
        )
        self.assertEqual(list(main.state.tickets), ["T1"])
        ticket = main.state.tickets["T1"]
        self.assertEqual(ticket.priority, "critical")
        self.assertEqual(ticket.status, "open")
        self.assertIsNone(ticket.assigned_to)
        self.assertEqual(main.state.counter, 1)
        self.assertIn("Ticket created: T1", printed)

    def test_a_bad_category_re_asks_and_then_creates(self):
        self.run_with_input(
            ["Projector dead", "billing", "hardware", "low", "1"], main.create_ticket
        )
        self.assertEqual(main.state.tickets["T1"].category, "hardware")

    def test_a_bad_affected_users_re_asks(self):
        self.run_with_input(
            ["Projector dead", "hardware", "low", "0", "-2", "3.5", "2"],
            main.create_ticket,
        )
        self.assertEqual(main.state.tickets["T1"].affected_users, 2)

    def test_a_retired_category_is_not_offered_for_new_tickets(self):
        from campusflow import categories

        categories.retire_category("administrative")
        _, printed = self.run_with_input(
            ["Legacy thing", "administrative", "other", "low", "1"], main.create_ticket
        )
        self.assertEqual(main.state.tickets["T1"].category, "other")
        self.assertIn("is not a valid category", printed)


class TestRejectedActionsChangeNothing(CliTestCase):
    def test_an_unassigned_ticket_cannot_start_work(self):
        main.state.tickets = {"T1": make_ticket("T1", status="open")}
        _, printed = self.run_with_input(["T1", "in_progress"], main.change_status)
        self.assertEqual(main.state.tickets["T1"].status, "open")
        self.assertIn("Not done:", printed)

    def test_a_resolved_ticket_cannot_take_a_note(self):
        main.state.tickets = {"T1": make_ticket("T1", status="resolved")}
        _, printed = self.run_with_input(
            ["T1", "Mentor A", "Trying anyway"], main.add_follow_up_note
        )
        self.assertEqual(main.state.tickets["T1"].notes, [])
        self.assertIn("reopen it first", printed)

    def test_a_short_note_is_refused_and_no_id_is_used(self):
        main.state.tickets = {"T1": make_ticket("T1")}
        self.run_with_input(["T1", "Mentor A", "hi"], main.add_follow_up_note)
        self.assertEqual(main.state.tickets["T1"].notes, [])

        self.run_with_input(["T1", "Mentor A", "Router reboot attempted"], main.add_follow_up_note)
        self.assertEqual(main.state.tickets["T1"].notes[0]["note_id"], "N001")

    def test_an_unknown_staff_choice_changes_nothing(self):
        main.state.tickets = {"T1": make_ticket("T1")}
        main.state.staff = ["Mentor A"]
        _, printed = self.run_with_input(["T1", "9"], main.assign)
        self.assertIsNone(main.state.tickets["T1"].assigned_to)
        self.assertIn("Invalid staff selection.", printed)


class TestNotesMenus(CliTestCase):
    def test_a_note_can_be_added_and_read_back(self):
        main.state.tickets = {"T1": make_ticket("T1")}
        _, printed = self.run_with_input(
            ["T1", "Mentor A", "Wi-Fi router reboot attempted"], main.add_follow_up_note
        )
        self.assertIn("Note N001 added to T1.", printed)

        _, printed = self.run_with_input(["T1"], main.view_ticket_notes)
        self.assertIn("N001 [Mentor A] Wi-Fi router reboot attempted", printed)

    def test_viewing_notes_on_a_ticket_with_none_says_so(self):
        main.state.tickets = {"T1": make_ticket("T1")}
        _, printed = self.run_with_input(["T1"], main.view_ticket_notes)
        self.assertIn("has no notes yet", printed)

    def test_viewing_notes_with_no_tickets_says_so(self):
        _, printed = self.run_with_input([], main.view_ticket_notes)
        self.assertIn("No tickets yet.", printed)


class TestWorkQueueOutput(CliTestCase):
    def test_shows_open_and_in_progress_only(self):
        main.state.tickets = {
            "T1": make_ticket("T1", status="open"),
            "T2": make_ticket("T2", status="resolved"),
        }
        _, printed = self.run_with_input([], main.work_queue)
        self.assertIn("T1", printed)
        self.assertNotIn("T2", printed)

    def test_an_empty_queue_says_so(self):
        _, printed = self.run_with_input([], main.work_queue)
        self.assertIn("No open or in-progress tickets.", printed)


class TestSearchOutput(CliTestCase):
    def test_search_prints_the_required_columns(self):
        main.state.tickets = {
            "T1": make_ticket(
                "T1", title="Wi-Fi down", category="network", assigned_to="Mentor A"
            )
        }
        _, printed = self.run_with_input(["wi-fi", "network", "open", ""], main.search)
        self.assertIn("T1 | wi-fi down | network |", printed)
        self.assertIn("1 ticket(s) matched.", printed)

    def test_an_invalid_filter_re_prompts_rather_than_matching_nothing(self):
        main.state.tickets = {"T1": make_ticket("T1", title="Wi-Fi down")}
        _, printed = self.run_with_input(
            ["wi-fi", "network", "closed", "open", ""], main.search
        )
        self.assertIn("1 ticket(s) matched.", printed)

    def test_no_match_says_so(self):
        main.state.tickets = {"T1": make_ticket("T1", title="Wi-Fi down")}
        _, printed = self.run_with_input(["printer", "", "", ""], main.search)
        self.assertIn("No tickets matched.", printed)


class TestSearchByPriority(CliTestCase):
    """The separate optional view: the same search, re-ordered.

    Requirement D keeps the Open Work Queue as it is and asks for the
    priority-ordered view to be something *additional*. This is that view, so it
    has to use the same filters and show the same tickets — only the order
    differs from the plain search.
    """

    def setUp(self):
        super().setUp()
        main.state.tickets = {
            "T1": make_ticket("T1", title="wi-fi down", urgency="low", affected_users=1),
            "T2": make_ticket("T2", title="wi-fi slow", urgency="high", affected_users=20),
            "T3": make_ticket("T3", title="wi-fi gone", urgency="medium", affected_users=3),
        }

    def results_in_order(self, printed):
        return [
            line.split(" | ")[0]
            for line in printed.splitlines()
            if " | " in line
        ]

    def test_puts_critical_first_then_the_rest_by_priority(self):
        _, printed = self.run_with_input(["wi-fi", "", "", ""], main.search_by_priority)
        self.assertEqual(self.results_in_order(printed), ["T2", "T3", "T1"])

    def test_plain_search_shows_the_same_tickets_in_id_order(self):
        """Only the order differs — the view is not a different filter."""
        _, by_id = self.run_with_input(["wi-fi", "", "", ""], main.search)
        _, by_priority = self.run_with_input(["wi-fi", "", "", ""], main.search_by_priority)
        self.assertEqual(self.results_in_order(by_id), ["T1", "T2", "T3"])
        self.assertEqual(
            sorted(self.results_in_order(by_priority)),
            sorted(self.results_in_order(by_id)),
        )

    def test_the_filters_still_apply(self):
        _, printed = self.run_with_input(["wi-fi", "", "open", "low"], main.search_by_priority)
        self.assertEqual(self.results_in_order(printed), ["T1"])

    def test_the_work_queue_is_not_affected(self):
        """Requirement D: the original queue keeps its own behaviour.

        It lists ``id priority status`` and shows open plus in_progress, so its
        order here is the same priority order — but reached through
        ``get_work_queue``, not through this view. Nothing about it changed.
        """
        _, printed = self.run_with_input([], main.work_queue)
        rows = [line for line in printed.splitlines() if line.startswith("T")]
        self.assertEqual(rows, ["T2 critical open", "T3 medium open", "T1 low open"])
        # the queue has its own format and does not use the search columns
        self.assertEqual(self.results_in_order(printed), [])


class TestCategoryMenu(CliTestCase):
    def test_adding_a_category_persists_it(self):
        from campusflow import categories

        _, printed = self.run_with_input(["1", "printing", "3"], main.manage_categories)
        self.assertIn("printing", categories.get_categories())
        self.assertIn("Category 'printing' added.", printed)
        self.assertTrue(main.storage.CATEGORIES_FILE.exists())

    def test_an_invalid_menu_choice_is_reported(self):
        _, printed = self.run_with_input(["9", "3"], main.manage_categories)
        self.assertIn("Invalid menu option.", printed)

    def test_retiring_the_last_category_is_refused(self):
        from campusflow import categories

        for name in ("network", "hardware", "software", "other"):
            categories.retire_category(name)
        self.assertEqual(categories.get_categories(), ["administrative"])

        _, printed = self.run_with_input(["2", "administrative", "3"], main.manage_categories)
        self.assertIn("Not done:", printed)
        self.assertEqual(categories.get_categories(), ["administrative"])


if __name__ == "__main__":
    unittest.main()
