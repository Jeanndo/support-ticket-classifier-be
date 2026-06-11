import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.roles import Role
from app.database import db
from app.dependencies.auth import require_roles
from app.models.schemas import AnalyticsResponse

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "",
    response_model=AnalyticsResponse,
    summary="Aggregated ticket metrics for dashboards",
)
def get_analytics(
    _user: dict = Depends(
        require_roles(Role.ADMIN, Role.MANAGER, Role.SUPPORT_AGENT)
    ),
):
    return AnalyticsResponse(**db.get_analytics())


@router.get(
    "/export",
    summary="Export ticket analytics and records to CSV",
    response_class=StreamingResponse,
)
def export_analytics_csv(
    _user: dict = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    analytics = db.get_analytics()
    tickets = db.get_all_tickets()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Smart Support Ticket Classifier — Analytics Export"])
    writer.writerow(["Generated", datetime.now(UTC).isoformat()])
    writer.writerow([])

    writer.writerow(["Metric", "Value"])
    for key, value in analytics.items():
        writer.writerow([key, value])

    writer.writerow([])
    writer.writerow(
        [
            "ticket_id",
            "summary",
            "category",
            "priority",
            "status",
            "confidence",
            "team",
            "assigned_to",
            "escalation",
            "created_at",
            "updated_at",
        ]
    )
    for t in tickets:
        writer.writerow(
            [
                t["ticket_id"],
                t["summary"],
                t["category"],
                t["priority"],
                t["status"],
                t["confidence"],
                t["team"],
                t.get("assigned_to_name") or "",
                t["escalation"],
                t["created_at"],
                t["updated_at"],
            ]
        )

    output.seek(0)
    filename = f"ticket-analytics-{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
