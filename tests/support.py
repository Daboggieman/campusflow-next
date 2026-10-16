"""Shared fixtures for the CampusFlow Next test suite.

Not itself a test module — ``unittest`` discovery only collects ``test*.py``,
so this file is imported by the test modules that need it.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from campusflow import categories, storage
from campusflow.priority import calculate_priority
from campusflow.tickets import Ticket


def make_ticket(
    ticket_id="T1",
    title="network issue",
    category="network",
    urgency="medium",
    affected_users=5,
    status="open",
    assigned_to=None,
    notes=None,
    priority=None,
):
    """Build a ``Ticket`` whose priority agrees with its urgency and user count.

    Consistency is not optional for fixtures that get saved: the storage layer
    refuses to load a record whose stored priority disagrees with the priority
    rules, precisely so a hand-edited file cannot go unnoticed. Deriving the
    priority here means a fixture can never accidentally be inconsistent.
    """
    if priority is None:
        priority = calculate_priority(urgency, affected_users)

    return Ticket(
        id=ticket_id,
        title=title,
        category=category,
        urgency=urgency,
        affected_users=affected_users,
        priority=priority,
        status=status,
        assigned_to=assigned_to,
        notes=[] if notes is None else notes,
    )


def make_note(note_id="N001", author="Mentor A", message="Router reboot attempted"):
    """A well-formed note dictionary."""
    return {"note_id": note_id, "author": author, "message": message}


class TemporaryDataDirTestCase(unittest.TestCase):
    """Base class giving each test a throwaway data folder.

    Also resets the category registry, which is module-level state: without
    this, a test that retires a category would leak into every test that runs
    after it.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        tmp = Path(self.tmpdir.name)

        patchers = [
            mock.patch.object(storage, "DATA_DIR", tmp),
            mock.patch.object(storage, "TICKETS_FILE", tmp / "tickets.json"),
            mock.patch.object(storage, "COUNTER_FILE", tmp / "counter.json"),
            mock.patch.object(storage, "STAFF_FILE", tmp / "staff.json"),
            mock.patch.object(storage, "CATEGORIES_FILE", tmp / "categories.json"),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        categories.reset_categories()
        self.addCleanup(categories.reset_categories)

    @property
    def tmp_path(self) -> Path:
        return Path(self.tmpdir.name)
