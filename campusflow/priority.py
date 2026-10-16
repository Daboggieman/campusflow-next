CRITICAL_USER_THRESHOLD = 10
AFFECTED_USER_THRESHOLD = 3

def calculate_priority(urgency, affected_users):
    if urgency == "high" and affected_users >= CRITICAL_USER_THRESHOLD:
        return "critical"
    if urgency == "high" or affected_users >= CRITICAL_USER_THRESHOLD:
        return "high"
    if urgency == "medium" or affected_users >= AFFECTED_USER_THRESHOLD:
        return "medium"
    return "low"
