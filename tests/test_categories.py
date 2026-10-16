"""The editable category list.

Engineer A — Ticket Safety and Storage Engineer.
The category list stopped being a constant in the source and became
application data, so it needs the same treatment as any other stored data:
validated on the way in, and equal to its default when it cannot be read.
"""

import json
import unittest

from campusflow import categories
from campusflow.errors import DataError, ValidationError
from support import TemporaryDataDirTestCase


class CategoryRegistryTestCase(unittest.TestCase):
    def setUp(self):
        categories.reset_categories()
        self.addCleanup(categories.reset_categories)


class TestDefaults(CategoryRegistryTestCase):
    def test_ships_with_the_five_original_categories(self):
        self.assertEqual(
            categories.get_categories(),
            ["network", "hardware", "software", "administrative", "other"],
        )

    def test_nothing_is_retired_to_begin_with(self):
        self.assertEqual(categories.get_retired_categories(), [])

    def test_the_returned_list_is_a_copy(self):
        """Mutating the returned list must not reach into the registry."""
        categories.get_categories().append("injected")
        self.assertNotIn("injected", categories.get_categories())


class TestAddCategory(CategoryRegistryTestCase):
    def test_adds_a_new_category(self):
        self.assertEqual(categories.add_category("Printing"), "printing")
        self.assertIn("printing", categories.get_categories())

    def test_refuses_a_duplicate(self):
        with self.assertRaises(ValidationError):
            categories.add_category("Network")

    def test_refuses_a_blank_name(self):
        with self.assertRaises(ValidationError):
            categories.add_category("   ")

    def test_refuses_a_non_text_name(self):
        with self.assertRaises(ValidationError):
            categories.add_category(7)

    def test_reviving_a_retired_category_keeps_its_stored_spelling(self):
        categories.retire_category("administrative")
        self.assertEqual(categories.add_category("Administrative"), "administrative")
        self.assertIn("administrative", categories.get_categories())
        self.assertNotIn("administrative", categories.get_retired_categories())


class TestRetireCategory(CategoryRegistryTestCase):
    def test_retires_an_active_category(self):
        categories.retire_category("administrative")
        self.assertNotIn("administrative", categories.get_categories())
        self.assertIn("administrative", categories.get_retired_categories())

    def test_a_retired_category_is_still_known(self):
        """This is what stops retiring a category orphaning its tickets."""
        categories.retire_category("administrative")
        self.assertIn("administrative", categories.get_known_categories())

    def test_refuses_an_unknown_category(self):
        with self.assertRaises(ValidationError):
            categories.retire_category("billing")

    def test_refuses_to_retire_the_last_category(self):
        for name in list(categories.get_categories())[:-1]:
            categories.retire_category(name)
        self.assertEqual(len(categories.get_categories()), 1)
        with self.assertRaises(ValidationError):
            categories.retire_category(categories.get_categories()[0])


class TestSetCategories(CategoryRegistryTestCase):
    def test_replaces_the_registry(self):
        categories.set_categories(["alpha", "beta"])
        self.assertEqual(categories.get_categories(), ["alpha", "beta"])

    def test_refuses_an_empty_active_list(self):
        with self.assertRaises(ValidationError):
            categories.set_categories([])

    def test_refuses_a_duplicate_active_name(self):
        with self.assertRaises(ValidationError):
            categories.set_categories(["alpha", "ALPHA"])

    def test_a_name_cannot_be_both_active_and_retired(self):
        categories.set_categories(["alpha"], ["alpha"])
        self.assertEqual(categories.get_retired_categories(), [])


class TestCategoryPersistence(TemporaryDataDirTestCase):
    def test_a_missing_file_is_seeded_with_the_defaults(self):
        from campusflow import storage

        categories.load_categories(storage.CATEGORIES_FILE)
        self.assertTrue(storage.CATEGORIES_FILE.exists())
        self.assertEqual(categories.get_categories(), categories.DEFAULT_CATEGORIES)

    def test_round_trips_through_a_file(self):
        from campusflow import storage

        categories.add_category("printing")
        categories.retire_category("administrative")
        categories.save_categories(storage.CATEGORIES_FILE)

        categories.reset_categories()
        self.assertNotIn("printing", categories.get_categories())

        categories.load_categories(storage.CATEGORIES_FILE)
        self.assertIn("printing", categories.get_categories())
        self.assertIn("administrative", categories.get_retired_categories())

    def test_accepts_a_plain_json_list_as_the_active_set(self):
        """A hand-written file should not have to know about the envelope."""
        from campusflow import storage

        storage.CATEGORIES_FILE.write_text(
            json.dumps(["network", "other"]), encoding="utf-8"
        )
        categories.load_categories(storage.CATEGORIES_FILE)
        self.assertEqual(categories.get_categories(), ["network", "other"])

    def test_rejects_unreadable_json(self):
        from campusflow import storage

        storage.CATEGORIES_FILE.write_text("{not json", encoding="utf-8")
        with self.assertRaises(DataError):
            categories.load_categories(storage.CATEGORIES_FILE)

    def test_rejects_an_envelope_without_an_active_list(self):
        from campusflow import storage

        storage.CATEGORIES_FILE.write_text(json.dumps({"retired": []}), encoding="utf-8")
        with self.assertRaises(DataError):
            categories.load_categories(storage.CATEGORIES_FILE)

    def test_rejects_an_empty_active_list_without_changing_the_registry(self):
        from campusflow import storage

        storage.CATEGORIES_FILE.write_text(
            json.dumps({"active": [], "retired": []}), encoding="utf-8"
        )
        with self.assertRaises(DataError):
            categories.load_categories(storage.CATEGORIES_FILE)
        self.assertEqual(categories.get_categories(), categories.DEFAULT_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
