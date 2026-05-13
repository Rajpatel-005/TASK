from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    mobile_number: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)




class RequestOTPResponse(BaseModel):
    message: str
    mobile_number: str
    otp: str
    valid_for_minutes: int

class VerifyOTPResponse(BaseModel):
    message: str
    user: UserResponse
    is_new_user: bool
    access_token: str
    token_type: str



class CurrentUserResponse(BaseModel):
    sub: str
    mobile_number: str
    exp: int

class CurrentUserWrapperResponse(BaseModel):
    user: CurrentUserResponse
