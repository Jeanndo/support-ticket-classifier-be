from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database.orm_models import Ticket, User
from app.database.session import SessionLocal

TICKET_STATUSES = (
    "Open",
    "In Progress",
    "Waiting Customer",
    "Resolved",
    "Closed",
)


def _session() -> Session:
    return SessionLocal()


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
    }


def _ticket_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "ticket_id": ticket.ticket_id,
        "ticket_text": ticket.ticket_text,
        "summary": ticket.summary,
        "category": ticket.category,
        "priority": ticket.priority,
        "confidence": ticket.confidence,
        "assessment": ticket.assessment,
        "team": ticket.team,
        "email": ticket.email,
        "sla": ticket.sla,
        "escalation": ticket.escalation,
        "keywords": ticket.keywords or [],
        "status": ticket.status,
        "assigned_to": ticket.assigned_to,
        "assigned_to_name": ticket.assignee.full_name if ticket.assignee else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    }


def init_db() -> None:
    from app.database.session import init_db as _init

    _init()


def create_user(email: str, hashed_password: str, full_name: str, role: str) -> dict:
    with _session() as session:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return _user_dict(user)


def get_user_by_email(email: str) -> dict | None:
    with _session() as session:
        user = session.scalar(select(User).where(User.email == email))
        return _user_dict(user) if user else None


def get_user_by_id(user_id: int) -> dict | None:
    with _session() as session:
        user = session.get(User, user_id)
        return _user_dict(user) if user else None


def list_users() -> list[dict]:
    with _session() as session:
        users = session.scalars(select(User).order_by(User.full_name)).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]


def user_count() -> int:
    with _session() as session:
        return session.scalar(select(func.count()).select_from(User)) or 0


def insert_ticket(row: dict, **timestamps: datetime | None) -> dict:
    now = datetime.now(UTC)
    created = timestamps.get("created_at") or now
    updated = timestamps.get("updated_at") or now
    resolved = timestamps.get("resolved_at")
    with _session() as session:
        ticket = Ticket(
            ticket_id=row["ticket_id"],
            ticket_text=row["ticket_text"],
            summary=row["summary"],
            category=row["category"],
            priority=row["priority"],
            confidence=float(row["confidence"]),
            assessment=row["assessment"],
            team=row["team"],
            email=row["email"],
            sla=row["sla"],
            escalation=bool(row["escalation"]),
            keywords=row["keywords"],
            status=row.get("status", "Open"),
            assigned_to=row.get("assigned_to"),
            created_at=created,
            updated_at=updated,
            resolved_at=resolved,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return _ticket_dict(ticket)


def get_ticket_by_id(ticket_id: str) -> dict | None:
    with _session() as session:
        ticket = session.scalar(
            select(Ticket)
            .options(joinedload(Ticket.assignee))
            .where(Ticket.ticket_id == ticket_id)
        )
        return _ticket_dict(ticket) if ticket else None


def enrich_ticket(row: dict) -> dict:
    if row.get("assigned_to") and not row.get("assigned_to_name"):
        user = get_user_by_id(row["assigned_to"])
        row["assigned_to_name"] = user["full_name"] if user else None
    elif not row.get("assigned_to"):
        row["assigned_to_name"] = None
    return row


def get_all_tickets(assigned_to: int | None = None) -> list[dict]:
    with _session() as session:
        query = select(Ticket).options(joinedload(Ticket.assignee))
        if assigned_to is not None:
            query = query.where(Ticket.assigned_to == assigned_to)
        query = query.order_by(Ticket.created_at.desc())
        tickets = session.scalars(query).unique().all()
        return [_ticket_dict(t) for t in tickets]


def update_ticket_status(ticket_id: str, status: str) -> dict | None:
    now = datetime.now(UTC)
    with _session() as session:
        ticket = session.scalar(
            select(Ticket)
            .options(joinedload(Ticket.assignee))
            .where(Ticket.ticket_id == ticket_id)
        )
        if not ticket:
            return None
        ticket.status = status
        ticket.updated_at = now
        if status in ("Resolved", "Closed"):
            ticket.resolved_at = ticket.resolved_at or now
        session.commit()
        session.refresh(ticket)
        return _ticket_dict(ticket)


def assign_ticket(ticket_id: str, assigned_to: int) -> dict | None:
    now = datetime.now(UTC)
    with _session() as session:
        ticket = session.scalar(
            select(Ticket)
            .options(joinedload(Ticket.assignee))
            .where(Ticket.ticket_id == ticket_id)
        )
        if not ticket:
            return None
        ticket.assigned_to = assigned_to
        ticket.status = "In Progress"
        ticket.updated_at = now
        session.commit()
    return get_ticket_by_id(ticket_id)


def get_analytics() -> dict:
    with _session() as session:
        total = session.scalar(select(func.count()).select_from(Ticket)) or 0

        cats = dict(
            session.execute(
                select(Ticket.category, func.count()).group_by(Ticket.category)
            ).all()
        )
        prios = dict(
            session.execute(
                select(Ticket.priority, func.count()).group_by(Ticket.priority)
            ).all()
        )
        statuses = dict(
            session.execute(
                select(Ticket.status, func.count()).group_by(Ticket.status)
            ).all()
        )
        escalated = (
            session.scalar(
                select(func.count()).select_from(Ticket).where(Ticket.escalation.is_(True))
            )
            or 0
        )
        avg_conf = session.scalar(select(func.avg(Ticket.confidence))) or 0.0

        resolved_rows = session.execute(
            select(Ticket.created_at, Ticket.resolved_at).where(
                Ticket.resolved_at.is_not(None)
            )
        ).all()

        sla_met = (
            session.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(
                    (Ticket.escalation.is_(False))
                    | (Ticket.status.in_(["Resolved", "Closed"]))
                )
            )
            or 0
        )

    resolution_hours: list[float] = []
    for created, resolved in resolved_rows:
        if created and resolved:
            resolution_hours.append((resolved - created).total_seconds() / 3600)

    avg_resolution = (
        round(sum(resolution_hours) / len(resolution_hours), 2)
        if resolution_hours
        else None
    )

    return {
        "total_tickets": total,
        "technical_issues": cats.get("Technical Issue", 0),
        "billing": cats.get("Billing", 0),
        "feature_requests": cats.get("Feature Request", 0),
        "security": cats.get("Security Issue", 0),
        "bug_reports": cats.get("Bug Report", 0),
        "account_access": cats.get("Account Access", 0),
        "high_priority": prios.get("High", 0),
        "medium_priority": prios.get("Medium", 0),
        "low_priority": prios.get("Low", 0),
        "open_tickets": statuses.get("Open", 0),
        "in_progress": statuses.get("In Progress", 0),
        "waiting_customer": statuses.get("Waiting Customer", 0),
        "resolved": statuses.get("Resolved", 0),
        "closed": statuses.get("Closed", 0),
        "escalated": escalated,
        "avg_confidence": round(float(avg_conf), 2),
        "avg_resolution_hours": avg_resolution,
        "sla_compliance_rate": round((sla_met / total * 100) if total else 100.0, 2),
    }


def ticket_count() -> int:
    with _session() as session:
        return session.scalar(select(func.count()).select_from(Ticket)) or 0
