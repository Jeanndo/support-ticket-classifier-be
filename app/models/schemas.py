from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class RoleEnum(str, Enum):
    admin = "admin"
    support_agent = "support_agent"
    manager = "manager"


class TicketStatusEnum(str, Enum):
    open = "Open"
    in_progress = "In Progress"
    waiting_customer = "Waiting Customer"
    resolved = "Resolved"
    closed = "Closed"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    full_name: str
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: RoleEnum
    created_at: datetime


class PredictRequest(BaseModel):
    ticket_text: str = Field(..., min_length=10, max_length=5000)


class PredictResponse(BaseModel):
    ticket_id: str
    summary: str
    category: str
    priority: str
    confidence: float
    assessment: str
    team: str
    email: str
    sla: str
    escalation: bool
    keywords: list[str]
    status: TicketStatusEnum = TicketStatusEnum.open
    assigned_to: int | None = None
    assigned_to_name: str | None = None


class TicketRecord(BaseModel):
    ticket_id: str
    ticket_text: str
    summary: str
    category: str
    priority: str
    confidence: float
    assessment: str
    team: str
    email: str
    sla: str
    escalation: bool
    keywords: list[str]
    status: TicketStatusEnum
    assigned_to: int | None = None
    assigned_to_name: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketStatusUpdate(BaseModel):
    status: TicketStatusEnum


class TicketAssignRequest(BaseModel):
    assigned_to: int


class AnalyticsResponse(BaseModel):
    total_tickets: int
    technical_issues: int
    billing: int
    feature_requests: int
    security: int
    bug_reports: int
    account_access: int
    high_priority: int
    medium_priority: int
    low_priority: int
    open_tickets: int
    in_progress: int
    waiting_customer: int
    resolved: int
    closed: int
    escalated: int
    avg_confidence: float
    avg_resolution_hours: float | None = None
    sla_compliance_rate: float


class DashboardEvent(BaseModel):
    event: str
    data: dict
