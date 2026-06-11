from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, verify_password
from app.database import db
from app.dependencies.auth import get_current_user
from app.models.schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate and receive JWT")
def login(body: LoginRequest):
    user = db.get_user_by_email(body.email)
    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        role=user["role"],
        full_name=user["full_name"],
        email=user["email"],
    )


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
def me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        created_at=datetime.fromisoformat(user["created_at"]),
    )
