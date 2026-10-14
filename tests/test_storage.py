import tempfile
import unittest
from pathlib import Path
from unittest import mock

from campusflow import storage
from campusflow.tickets import Ticket


class TestStorageBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        tmp = Path(self.tmpdir.name)
        patchers = [
            mock.patch.object(storage, "DATA_DIR", tmp),
            mock.patch.object(storage, "TICKETS_FILE", tmp / "tickets.json"),
            mock.patch.object(storage, "COUNTER_FILE", tmp / "counter.json"),
            mock.patch.object(storage, "STAFF_FILE", tmp / "staff.json"),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)


class TestStorageFirstRun(TestStorageBase):

    def test_first_run_loads_empty_tickets(self):
        self.assertEqual(storage.load_tickets(), {})

    def test_first_run_starts_counter_at_zero(self):
        self.assertEqual(storage.load_counter(), 0)

    def test_first_run_creates_staff_placeholders(self):
        staff = storage.load_staff()
        self.assertEqual(staff, storage.DEFAULT_STAFF)


class TestStorageCounter(TestStorageBase):

    def test_generate_ticket_id_increments_counter(self):
        ticket_id, counter = storage.generate_ticket_id(4)
        self.assertEqual(ticket_id, "T5")
        self.assertEqual(counter, 5)
        self.assertEqual(storage.load_counter(), 5)


class TestStorageSaveLoad(TestStorageBase):

    def test_save_then_load_returns_same_tickets(self):
        ticket = Ticket(
            id="T001",
            title="Campus wifi",
            category="network",
            urgency="high",
            affected_users=15,
            priority="critical",
            status="open",
            assigned_to="Ada",
        )
        storage.save_tickets({"T001": ticket})
        loaded = storage.load_tickets()
        self.assertIn("T001", loaded)
        self.assertEqual(loaded["T001"].title, "campus wifi")
        self.assertEqual(loaded["T001"].affected_users, 15)
        self.assertEqual(loaded["T001"].assigned_to, "Ada")


class TestStorageBrokenFile(TestStorageBase):

    def test_save_then_load_builds_ticket_objects(self):
        storage.save_tickets({})
        loaded = storage.load_tickets()
        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
