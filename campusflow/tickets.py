from dataclasses import dataclass
categories = ["network", "hardware", "software", "administrative", "other"]
urgencies = ["low", "medium", "high", "critical"]

def check_title(raw_title: str):
    title = raw_title.strip().lower()
    if not title:
        raise ValueError("Title cannot be blank")
    return title

def check_category(raw_category: str) -> str:
    for category in categories:
        if category.casefold() == raw_category.casefold():
            return category
    raise ValueError(f"Choose one of: {', '.join(categories)}.")
    
def check_urgency(raw_urgency: str) -> str:
    for urgency in urgencies:
        if urgency.casefold() == raw_urgency.casefold():
            return urgency
    raise ValueError(f"Choose one of: {', '.join(urgencies)}.")

def check_affected_users(raw_affected_users: str) -> int:
    try:
        affected_users = int(raw_affected_users)
    except ValueError:
        raise ValueError("Affected users must be an integer.")
    if affected_users <= 0:
        raise ValueError("Affected users cannot be less than 1.")
    return affected_users

@dataclass(frozen=False)
class Ticket:
    id: str
    title: str
    category: str
    urgency: str
    affected_users: int
    priority: str
    status: str
    assigned_to: bool

    def __post_init__(self):
        self.title = check_title(self.title)
        self.category = check_category(self.category)
        self.urgency = check_urgency(self.urgency)
        self.affected_users = check_affected_users(self.affected_users)
        
