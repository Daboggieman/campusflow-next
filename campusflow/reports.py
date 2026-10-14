from collections import Counter

def generate_report(tickets):

    status_counts = Counter(
        ticket.status for ticket in tickets.values()
    )

    priority_counts = Counter(
        ticket.priority for ticket in tickets.values()
    )

    return {
        "total": len(tickets),
        "by_status": dict(status_counts),
        "by_priority": dict(priority_counts),
    }


def print_report(report):
    if report["total"] == 0:
        print("No tickets yet.")
        return

    print("\nCampusFlow Ticket")
    print(f"Total tickets: {report['total']}")

    print("\nTickets by status:")
    for status in ("open", "in_progress", "resolved"):
        count = report["by_status"].get(status, 0)
        print(f"  {status}: {count}")

    print("\nTickets by priority:")
    for priority in ("critical", "high", "medium", "low"):
        count = report["by_priority"].get(priority, 0)
        print(f"  {priority}: {count}")