from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.services.auth_service import authenticate_user, create_access_token, user_to_dict

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut(**user_to_dict(user)))
