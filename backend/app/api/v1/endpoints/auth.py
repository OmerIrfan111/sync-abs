from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.login_throttle import clear_failures, ensure_not_locked, record_failure
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserResponse, UserCreate, LoginRequest, ChangePasswordRequest
from app.api.deps import get_current_user

router = APIRouter()


def _login(db: Session, email: str, password: str) -> dict:
    ensure_not_locked(email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        record_failure(email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    clear_failures(email)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login."""
    return _login(db, form_data.username, form_data.password)


@router.post("/login/json", response_model=Token)
def login_json(
    body: LoginRequest,
    db: Session = Depends(get_db)
):
    """JSON body login for frontend convenience."""
    return _login(db, body.email, body.password)


@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user details."""
    return current_user


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lets any signed-in user change their own password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Your current password is not correct.")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="Choose a password that is different from your current one.")
    if body.new_password.strip().lower() == current_user.email.strip().lower():
        raise HTTPException(status_code=400, detail="Your password can't be the same as your email.")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"success": True, "message": "Password changed."}
