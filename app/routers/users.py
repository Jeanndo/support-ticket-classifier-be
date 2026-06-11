from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.roles import Role
from app.database import db
from app.dependencies.auth import get_current_user, require_roles
from app.models.schemas import UserResponse

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List users available for ticket assignment",
)
def list_users(
    _user: dict = Depends(require_roles(Role.ADMIN, Role.MANAGER)),
):
    return [
        UserResponse(
            id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            created_at=datetime.fromisoformat(u["created_at"]),
        )
        for u in db.list_users()
        if u["role"] in (Role.SUPPORT_AGENT.value, Role.MANAGER.value)
    ]
