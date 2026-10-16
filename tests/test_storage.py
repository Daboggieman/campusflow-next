"""Persistence: strict loading, ID continuity, and notes round-tripping.

Engineer A — Ticket Safety and Storage Engineer.
Covers milestones A5 and A6: a corrupted or duplicated file is refused without
erasing what is already in memory, and after a reload the next IDs are correct.
"""

import json
import unittest

from campusflow import categories, storage
from campusflow.errors import DataError
from support import TemporaryDataDirTestCase, make_note, make_ticket


class TestStorageBase(TemporaryDataDirTestCase):
    """Kept as the shared base name the original tests used."""


class TestStorageFirstRun(TestStorageBase):
    def test_first_run_loads_empty_tickets(self):
        self.assertEqual(storage.load_tickets(), {})

    def test_first_run_starts_counter_at_zero(self):
        self.assertEqual(storage.load_counter(), 0)

    def test_first_run_creates_staff_placeholders(self):
        staff = storage.load_staff()
        self.assertEqual(staff, storage.DEFAULT_STAFF)

    def test_load_application_data_creates_every_file(self):
        data = storage.load_application_data()
        self.assertEqual(data.tickets, {})
        self.assertEqual(data.counter, 0)
        self.assertEqual(data.warnings, [])
        for path in (
            storage.TICKETS_FILE,
            storage.COUNTER_FILE,
            storage.STAFF_FILE,
            storage.CATEGORIES_FILE,
        ):
            self.assertTrue(path.exists(), msg=f"{path} was not created")


class TestStorageCounter(TestStorageBase):
    def test_generate_ticket_id_increments_counter(self):
        ticket_id, counter = storage.generate_ticket_id(4)
        self.assertEqual(ticket_id, "T5")
        self.assertEqual(counter, 5)
        self.assertEqual(storage.load_counter(), 5)

    def test_next_ticket_id_does_not_write_anything(self):
        """The preview form leaves the counter file alone."""
        ticket_id, counter = storage.next_ticket_id(4)
        self.assertEqual((ticket_id, counter), ("T5", 5))
        self.assertEqual(storage.load_counter(), 0)

    def test_counter_is_raised_to_the_highest_saved_ticket(self):
        tickets = {"T1": make_ticket("T1"), "T7": make_ticket("T7")}
        counter, warnings = storage.validate_counter(2, tickets)
        self.assertEqual(counter, 7)
        self.assertEqual(len(warnings), 1)
        self.assertIn("T7", warnings[0])

    def test_a_correct_counter_is_left_alone(self):
        tickets = {"T1": make_ticket("T1"), "T2": make_ticket("T2")}
        counter, warnings = storage.validate_counter(5, tickets)
        self.assertEqual((counter, warnings), (5, []))

    def test_reload_continues_id_generation_without_colliding(self):
        """The stored counter is deliberately too low for the tickets present."""
        storage.save_tickets({"T1": make_ticket("T1"), "T2": make_ticket("T2")})
        storage.save_counter(1)

        data = storage.load_application_data()
        self.assertEqual(len(data.warnings), 1)
        self.assertEqual(data.counter, 2)
        self.assertEqual(storage.load_counter(), 2)

        next_id, _ = storage.generate_ticket_id(data.counter)
        self.assertEqual(next_id, "T3")
        self.assertNotIn(next_id, data.tickets)


class TestStorageSaveLoad(TestStorageBase):
    def test_save_then_load_returns_same_tickets(self):
        ticket = make_ticket("T001", title="Campus wifi", urgency="high", affected_users=15, assigned_to="Ada")
        storage.save_tickets({"T001": ticket})
        loaded = storage.load_tickets()
        self.assertIn("T001", loaded)
        self.assertEqual(loaded["T001"].title, "campus wifi")
        self.assertEqual(loaded["T001"].affected_users, 15)
        self.assertEqual(loaded["T001"].assigned_to, "Ada")

    def test_notes_survive_a_save_and_load(self):
        ticket = make_ticket(
            "T1",
            notes=[make_note("N001", "Mentor A", "Router reboot attempted"),
                   make_note("N002", "Mentor B", "Investigating switch ports")],
        )
        storage.save_tickets({"T1": ticket})

        loaded = storage.load_tickets()["T1"]
        self.assertEqual(len(loaded.notes), 2)
        self.assertEqual(loaded.notes[0]["note_id"], "N001")
        self.assertEqual(loaded.notes[1]["author"], "Mentor B")
        self.assertEqual(loaded.notes[1]["message"], "Investigating switch ports")

    def test_the_next_note_id_survives_a_reload(self):
        from campusflow.notes import next_note_id

        ticket = make_ticket("T1", notes=[make_note("N001"), make_note("N002")])
        storage.save_tickets({"T1": ticket})
        self.assertEqual(next_note_id(storage.load_tickets()["T1"]), "N003")

    def test_saving_writes_every_field_including_notes(self):
        storage.save_tickets({"T1": make_ticket("T1", notes=[make_note("N001")])})
        raw = json.loads(storage.TICKETS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(raw["T1"]),
            ["affected_users", "assigned_to", "category", "id", "notes",
             "priority", "status", "title", "urgency"],
        )

    def test_saving_leaves_no_temporary_files_behind(self):
        storage.save_tickets({"T1": make_ticket("T1")})
        leftovers = [path.name for path in self.tmp_path.iterdir() if path.suffix == ".tmp"]
        self.assertEqual(leftovers, [])

    def test_load_application_data_wires_the_categories_in_first(self):
        """Tickets are validated against the known categories, so order matters."""
        storage.save_tickets({"T1": make_ticket("T1", category="administrative", urgency="low", affected_users=1)})
        data = storage.load_application_data()
        self.assertEqual(data.tickets["T1"].category, "administrative")
        self.assertEqual(categories.get_categories(), categories.DEFAULT_CATEGORIES)


class TestStorageRejectsBadData(TestStorageBase):
    """Every case must raise DataError rather than return a partial result."""

    def assert_rejected(self, text, expected_fragment=None):
        storage.TICKETS_FILE.write_text(text, encoding="utf-8")
        with self.assertRaises(DataError) as caught:
            storage.load_tickets()
        if expected_fragment:
            self.assertIn(expected_fragment, str(caught.exception))
        return caught.exception

    def test_duplicate_ticket_id_is_rejected(self):
        """Bug-hunter test BH-1 — see docs/bug-hunter-tests.md.

        ``json.load`` keeps the *last* of two identical keys without
        complaining, so a duplicated ticket ID used to make one ticket vanish
        silently. Refusing the file is the only safe answer.
        """
        first = json.dumps({"id": "T1", "title": "first", "category": "network",
                            "urgency": "low", "affected_users": 1, "priority": "low",
                            "status": "open", "assigned_to": None})
        second = json.dumps({"id": "T1", "title": "second", "category": "network",
                             "urgency": "low", "affected_users": 1, "priority": "low",
                             "status": "open", "assigned_to": None})
        self.assert_rejected(f'{{"T1": {first}, "T1": {second}}}', "Duplicate key")

    def test_corrupt_json_is_rejected(self):
        self.assert_rejected("{not json", "not valid JSON")

    def test_a_key_that_disagrees_with_the_stored_id_is_rejected(self):
        record = {"id": "T7", "title": "mismatch", "category": "network",
                  "urgency": "low", "affected_users": 1, "priority": "low",
                  "status": "open", "assigned_to": None}
        self.assert_rejected(json.dumps({"T1": record}), "does not match")

    def test_an_inconsistent_priority_is_rejected(self):
        record = {"id": "T1", "title": "wrong priority", "category": "network",
                  "urgency": "high", "affected_users": 20, "priority": "low",
                  "status": "open", "assigned_to": None}
        self.assert_rejected(json.dumps({"T1": record}), "implies 'critical'")

    def test_a_malformed_note_is_rejected(self):
        record = {"id": "T1", "title": "bad note", "category": "network",
                  "urgency": "low", "affected_users": 1, "priority": "low",
                  "status": "open", "assigned_to": None,
                  "notes": [{"note_id": "N001", "author": "Mentor A", "message": "no"}]}
        self.assert_rejected(json.dumps({"T1": record}), "at least")

    def test_a_top_level_list_is_rejected(self):
        self.assert_rejected(json.dumps([{"id": "T1"}]), "must contain a JSON object")

    def test_a_broken_counter_file_is_rejected(self):
        storage.COUNTER_FILE.write_text("banana", encoding="utf-8")
        with self.assertRaises(DataError):
            storage.load_counter()

    def test_a_negative_counter_is_rejected(self):
        storage.COUNTER_FILE.write_text("-1", encoding="utf-8")
        with self.assertRaises(DataError):
            storage.load_counter()

    def test_a_broken_staff_file_is_rejected(self):
        storage.STAFF_FILE.write_text(json.dumps([1, 2]), encoding="utf-8")
        with self.assertRaises(DataError):
            storage.load_staff()


class TestFailedLoadKeepsMemoryIntact(TestStorageBase):
    """The requirement the whole strict-load design exists to satisfy."""

    def test_a_failed_reload_does_not_erase_what_is_in_memory(self):
        storage.save_tickets({"T1": make_ticket("T1")})
        live = storage.load_tickets()
        self.assertEqual(list(live), ["T1"])

        # The file is now corrupted *after* the app already loaded it.
        storage.TICKETS_FILE.write_text("{not json", encoding="utf-8")

        try:
            live = storage.load_tickets()
        except DataError:
            pass  # main.py offers quit-or-start-fresh here instead of crashing
        self.assertEqual(list(live), ["T1"])

    def test_a_partially_valid_file_does_not_replace_memory(self):
        """The first record is fine and the second is not. Nothing is loaded."""
        good = {"id": "T1", "title": "fine", "category": "network", "urgency": "low",
                "affected_users": 1, "priority": "low", "status": "open",
                "assigned_to": None}
        bad = {"id": "T2", "title": "broken", "category": "network", "urgency": "low",
               "affected_users": 1, "priority": "critical", "status": "open",
               "assigned_to": None}
        storage.TICKETS_FILE.write_text(
            json.dumps({"T1": good, "T2": bad}), encoding="utf-8"
        )

        live = {"T9": make_ticket("T9")}
        try:
            live = storage.load_tickets()
        except DataError:
            pass
        self.assertEqual(list(live), ["T9"])


class TestStartFreshBackup(TestStorageBase):
    def test_backing_up_a_file_preserves_its_contents(self):
        storage.TICKETS_FILE.write_text("{broken", encoding="utf-8")
        backup = storage.backup_broken_file(storage.TICKETS_FILE)
        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_text(encoding="utf-8"), "{broken")

    def test_backing_up_a_missing_file_is_harmless(self):
        self.assertIsNone(storage.backup_broken_file(self.tmp_path / "absent.json"))


if __name__ == "__main__":
    unittest.main()
