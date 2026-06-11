from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    SUPPORT_AGENT = "support_agent"
    MANAGER = "manager"


TICKET_STATUSES = (
    "Open",
    "In Progress",
    "Waiting Customer",
    "Resolved",
    "Closed",
)

ROLE_LABELS = {
    Role.ADMIN: "Admin",
    Role.SUPPORT_AGENT: "Support Agent",
    Role.MANAGER: "Manager",
}
