from collections import Counter
from campusflow.categories import get_known_categories
from campusflow.tickets import PRIORITIES, STATUSES

REPORTED_STATUSES = STATUSES
REPORTED_PRIORITIES = PRIORITIES

def generate_report(tickets) -> dict:
    by_status = Counter(ticket.status for ticket in tickets.values())
    by_priority = Counter(ticket.priority for ticket in tickets.values())
    by_category = Counter(ticket.category for ticket in tickets.values())
    total = len(tickets)
    resolved = by_status.get("resolved", 0)
    unresolved = by_status.get("open", 0) + by_status.get("in_progress", 0)
    resolution_percentage = (resolved / total * 100) if total else 0.0

    return {
        "total": total,
        "by_status": dict(by_status),
        "by_priority": dict(by_priority),
        "by_category": dict(by_category),
        "unresolved": unresolved,
        "resolved": resolved,
        "resolution_percentage": round(resolution_percentage, 1),
    }

def _print_counts(title, order, counts, extra_keys=()):
    print(f"\n{title}")
    for key in order:
        print(f"  {key}: {counts.get(key, 0)}")
    for key in sorted(extra_keys):
        print(f"  {key}: {counts.get(key, 0)}")

def print_report(report) -> None:
    """display a report produced by :func:`generate_report`."""
    if report["total"] == 0:
        print("No tickets yet.")
        print("Resolution: 0.0% (0 of 0 resolved)")
        return

    print("\nCampusFlow Ticket")
    print(f"Total tickets: {report['total']}")

    _print_counts("Tickets by status:", REPORTED_STATUSES, report["by_status"])
    _print_counts("Tickets by priority:", REPORTED_PRIORITIES, report["by_priority"])

    known = set(get_known_categories())
    _print_counts(
        "Tickets by category:",
        [name for name in get_known_categories() if name in report["by_category"]],
        report["by_category"],
        extra_keys=[name for name in report["by_category"] if name not in known],
    )

    print("\nResolution:")
    print(f"  unresolved (open + in_progress): {report['unresolved']}")
    print(f"  resolved: {report['resolved']}")
    print(
        f"  resolution: {report['resolution_percentage']}% "
        f"({report['resolved']} of {report['total']} resolved)"
    )
