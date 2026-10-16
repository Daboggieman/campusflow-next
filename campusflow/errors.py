"""Error types shared by the CampusFlow modules.

Two failure families, deliberately kept apart:

``ValidationError``
    A **user action** broke a business rule: a blank title, a bad urgency, a
    note on a resolved ticket. The caller is expected to show the message and
    re-prompt. It subclasses ``ValueError`` so that every check written before
    this module existed (which raised plain ``ValueError``) is still caught by
    older ``except``/``assertRaises`` clauses.

``DataError``
    **Stored data** cannot be trusted: unreadable JSON, a duplicate ticket ID,
    a record that fails validation. The caller must not fall back to a partial
    load. It is deliberately *not* a ``ValueError`` so the two cases cannot be
    confused by a broad ``except ValueError``.
"""


class ValidationError(ValueError):
    """A user-supplied value failed a business rule. Safe to show and re-ask."""


class DataError(Exception):
    """Stored data is unusable. Callers must keep their current state intact."""
