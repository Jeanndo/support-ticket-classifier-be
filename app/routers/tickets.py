import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.roles import Role
from app.database import db
from app.dependencies.auth import get_current_user, require_roles
from app.models.schemas import (
    PredictRequest,
    PredictResponse,
    TicketAssignRequest,
    TicketRecord,
    TicketStatusEnum,
    TicketStatusUpdate,
)
from app.services.classifier import TicketClassifierService
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


def get_classifier() -> TicketClassifierService:
    return TicketClassifierService.get_instance()


def _keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        parsed = json.loads(value)
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    return []


def _to_record(row: dict) -> TicketRecord:
    return TicketRecord(
        ticket_id=row["ticket_id"],
        ticket_text=row["ticket_text"],
        summary=row["summary"],
        category=row["category"],
        priority=row["priority"],
        confidence=row["confidence"],
        assessment=row["assessment"],
        team=row["team"],
        email=row["email"],
        sla=row["sla"],
        escalation=bool(row["escalation"]),
        keywords=_keywords(row.get("keywords")),
        status=row["status"],
        assigned_to=row.get("assigned_to"),
        assigned_to_name=row.get("assigned_to_name"),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _to_predict(row: dict) -> PredictResponse:
    return PredictResponse(
        ticket_id=row["ticket_id"],
        summary=row["summary"],
        category=row["category"],
        priority=row["priority"],
        confidence=row["confidence"],
        assessment=row["assessment"],
        team=row["team"],
        email=row["email"],
        sla=row["sla"],
        escalation=bool(row["escalation"]),
        keywords=_keywords(row.get("keywords")),
        status=row["status"],
        assigned_to=row.get("assigned_to"),
        assigned_to_name=row.get("assigned_to_name"),
    )


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Classify a support ticket using ML + business rules",
)
async def predict_ticket(
    body: PredictRequest,
    user: dict = Depends(
        require_roles(Role.ADMIN, Role.SUPPORT_AGENT, Role.MANAGER)
    ),
    classifier: TicketClassifierService = Depends(get_classifier),
):
    text = body.ticket_text.strip()
    if len(text) < 10:
        raise HTTPException(status_code=422, detail="Ticket text must be at least 10 characters")
    try:
        result = classifier.classify(text)
        result["status"] = "Open"
        saved = db.insert_ticket(result)
        enriched = db.get_ticket_by_id(saved["ticket_id"])
        if enriched:
            enriched = db.enrich_ticket(enriched)
        record = _to_predict(enriched or saved)
        await ws_manager.broadcast("ticket_created", record.model_dump(mode="json"))
        await ws_manager.broadcast("analytics_updated", db.get_analytics())
        return record
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Classification failed") from exc


@router.get(
    "",
    response_model=list[TicketRecord],
    summary="List tickets (agents see assigned only; managers/admins see all)",
)
def list_tickets(user: dict = Depends(get_current_user)):
    if user["role"] == Role.SUPPORT_AGENT.value:
        rows = db.get_all_tickets(assigned_to=user["id"])
    else:
        rows = db.get_all_tickets()
    return [_to_record(r) for r in rows]


@router.patch(
    "/{ticket_id}/status",
    response_model=TicketRecord,
    summary="Update ticket workflow status",
)
async def update_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    user: dict = Depends(get_current_user),
):
    ticket = db.get_ticket_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if user["role"] == Role.SUPPORT_AGENT.value:
        if ticket.get("assigned_to") != user["id"]:
            raise HTTPException(status_code=403, detail="Not assigned to this ticket")

    updated = db.update_ticket_status(ticket_id, body.status.value)
    if updated is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updated = db.enrich_ticket(updated)
    record = _to_record(updated)
    await ws_manager.broadcast("ticket_updated", record.model_dump(mode="json"))
    await ws_manager.broadcast("analytics_updated", db.get_analytics())
    return record


@router.post(
    "/{ticket_id}/assign",
    response_model=TicketRecord,
    summary="Assign ticket to a support agent (manager/admin)",
)
async def assign_ticket(
    ticket_id: str,
    body: TicketAssignRequest,
    _user: dict = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    agent = db.get_user_by_id(body.assigned_to)
    if agent is None or agent["role"] not in (
        Role.SUPPORT_AGENT.value,
        Role.MANAGER.value,
    ):
        raise HTTPException(status_code=400, detail="Invalid assignee")

    updated = db.assign_ticket(ticket_id, body.assigned_to)
    if updated is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updated = db.enrich_ticket(updated)
    record = _to_record(updated)
    await ws_manager.broadcast("ticket_assigned", record.model_dump(mode="json"))
    await ws_manager.broadcast("analytics_updated", db.get_analytics())
    return record
