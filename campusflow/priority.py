"""The priority rules.

Kept exactly as first written, because this ordering is an acceptance rule:
the first match wins, and rule 1 sits above rule 2 only so that "critical" is
reachable at all — every critical ticket also satisfies rule 2.

Thresholds are named now instead of being repeated as literals, so a policy
change is one edit. The unreachable third branch of the original chain
("medium *and* 10 or more", which rule 2 always caught first) is gone; removing
it changes no output.

Note that ``urgency`` no longer includes the value "critical" — see
:mod:`campusflow.tickets`. "critical" is a priority, not an urgency.
"""

CRITICAL_USER_THRESHOLD = 10
AFFECTED_USER_THRESHOLD = 3


def calculate_priority(urgency, affected_users):
    """Return critical / high / medium / low for an urgency and user count."""
    if urgency == "high" and affected_users >= CRITICAL_USER_THRESHOLD:
        return "critical"
    if urgency == "high" or affected_users >= CRITICAL_USER_THRESHOLD:
        return "high"
    if urgency == "medium" or affected_users >= AFFECTED_USER_THRESHOLD:
        return "medium"
    return "low"
