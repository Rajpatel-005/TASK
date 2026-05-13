import os
from datetime import datetime, timedelta, timezone
from random import randint

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session



from src.db import (
    SQLAlchemyError,
    delete_otp_code,
    get_or_create_user,
    get_otp_code,
    get_postgres_db,
    is_otp_expired,
    upsert_otp_code,
)
from src.schemas import (
    CurrentUserWrapperResponse,
    RequestOTPResponse,
    UserResponse,
    VerifyOTPResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])



OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "5"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
SECRET_KEY = os.getenv("SECRET_KEY", "chat-app-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
security = HTTPBearer()




class MobileNumberRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)



class OTPVerifyRequest(BaseModel):
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=6)


def create_access_token(user: UserResponse) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "mobile_number": user.mobile_number,
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)





def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):

    return decode_access_token(credentials.credentials)



@router.get("/me", response_model=CurrentUserWrapperResponse)
def get_me(current_user=Depends(get_current_user)):
    return {"user": current_user}


@router.post("/request-otp", response_model=RequestOTPResponse)
def request_otp(
    data: MobileNumberRequest,
    postgres_db: Session = Depends(get_postgres_db),):

    otp = f"{randint(1000, 9999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    try:
        upsert_otp_code(postgres_db, data.mobile_number, otp, expires_at)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"PostgreSQL error: {exc}") from exc

    return {
        "message": "OTP sent successfully",
        "mobile_number": data.mobile_number,
        "otp": otp,
        "valid_for_minutes": OTP_EXPIRY_MINUTES,
    }


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(
    data: OTPVerifyRequest,
    postgres_db: Session = Depends(get_postgres_db),
):
    
    try:
    
        stored_otp = get_otp_code(postgres_db, data.mobile_number)
    
    
        if not stored_otp:
            raise HTTPException(status_code=404, detail="OTP not found for this mobile number")
        if is_otp_expired(stored_otp):
            delete_otp_code(postgres_db, stored_otp)
            raise HTTPException(status_code=400, detail="OTP has expired")
        if data.otp != stored_otp.otp_code:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        user, is_new_user = get_or_create_user(postgres_db, data.mobile_number)
        user = UserResponse.model_validate(user)
        delete_otp_code(postgres_db, stored_otp)

    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"PostgreSQL error: {exc}") from exc


    return {
        "message": "OTP verified successfully",
        "user": user,
        "is_new_user": is_new_user,
        "access_token": create_access_token(user),
        "token_type": "bearer",
    }
