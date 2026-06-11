import random
from datetime import UTC, datetime, timedelta

from app.core.roles import Role
from app.core.security import hash_password
from app.database import db
from app.services.classifier import TicketClassifierService

DEMO_USERS = [
    ("admin@company.com", "admin123", "Alex Admin", Role.ADMIN.value),
    ("manager@company.com", "manager123", "Morgan Manager", Role.MANAGER.value),
    ("agent@company.com", "agent123", "Sam Agent", Role.SUPPORT_AGENT.value),
    ("agent2@company.com", "agent123", "Jordan Support", Role.SUPPORT_AGENT.value),
]

DEMO_TICKETS = [
    "API requests are timing out and production integration keeps failing",
    "Unable to reset password after multiple login attempts on mobile app",
    "Credit card declined during subscription renewal billing cycle",
    "Security vulnerability report: possible XSS in user profile page",
    "Application crashes when uploading files larger than 10MB",
    "Need dark mode and dashboard filters for the analytics page",
    "Webhook failing for Stripe payment notifications in production",
    "Account locked after too many failed login attempts",
    "Urgent: production outage affecting all EU customers since 2am",
    "Feature request: export reports to CSV from admin panel",
    "Bug report: button not working on checkout page in Safari",
    "Billing inquiry about unexpected charge on last invoice",
    "Hack attempt detected on admin login endpoint",
    "Slow application performance when loading customer dashboard",
    "Integration not working with Salesforce CRM sync",
    "Request refund for duplicate billing charge this month",
    "Production database connection pool exhausted causing downtime",
    "Add notification system for ticket status updates",
    "Login page keeps refreshing after SSO authentication",
    "Security breach alert: unauthorized API key usage detected",
    "Unexpected error message when saving team settings",
    "Need reporting feature with custom date range filters",
    "Payment failed for enterprise plan renewal",
    "Technical issue: Redis cache invalidation causing stale data",
    "Feature request: mobile app push notifications",
]

STATUSES = ["Open", "In Progress", "Waiting Customer", "Resolved", "Closed"]


def seed_users() -> dict[str, int]:
    ids: dict[str, int] = {}
    for email, password, name, role in DEMO_USERS:
        existing = db.get_user_by_email(email)
        if existing:
            ids[email] = existing["id"]
            continue
        user = db.create_user(email, hash_password(password), name, role)
        ids[email] = user["id"]
    return ids


def seed_tickets(user_ids: dict[str, int]) -> None:
    if db.ticket_count() > 0:
        return

    classifier = TicketClassifierService.get_instance()
    agent_ids = [user_ids["agent@company.com"], user_ids["agent2@company.com"]]
    now = datetime.now(UTC)

    for text in DEMO_TICKETS:
        result = classifier.classify(text)
        created = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
        status = random.choices(STATUSES, weights=[20, 25, 15, 25, 15])[0]
        assigned = random.choice(agent_ids) if status != "Open" else None
        resolved_at = (
            created + timedelta(hours=random.randint(1, 48))
            if status in ("Resolved", "Closed")
            else None
        )

        result["status"] = status
        result["assigned_to"] = assigned
        db.insert_ticket(
            result,
            created_at=created,
            updated_at=created,
            resolved_at=resolved_at,
        )


def run_seed() -> None:
    if db.user_count() == 0:
        user_ids = seed_users()
    else:
        user_ids = {u["email"]: u["id"] for u in db.list_users()}
    seed_tickets(user_ids)
