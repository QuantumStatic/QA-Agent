from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.schemas import AuthRequest, AuthResponse
from app.auth.service import create_user, authenticate
from app.auth.jwt_utils import create_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    try:
        user = create_user(db, req.email, req.password)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return AuthResponse(token=create_token(str(user.id), user.email))


@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = authenticate(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(token=create_token(str(user.id), user.email))
