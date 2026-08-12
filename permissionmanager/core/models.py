from pydantic import BaseModel
from datetime import datetime

class FtpUserBase(BaseModel):
    user_name: str
    description: str
    ding_id: str
    email: str
    pass_word: str



class UserResponse(BaseModel):
    name: str
    description: str
    dingtalk_id: str
    email: str
    password: str
    created_at: datetime

class UserListResponse(BaseModel):
    users: list[UserResponse] | None

class GroupResponse(BaseModel):
    name: str
    description: str

class GroupListResponse(BaseModel):
    users: list[GroupResponse] | None

