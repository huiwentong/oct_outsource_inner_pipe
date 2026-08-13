from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FtpUserBase(BaseModel):
    name: str
    description: str
    ding_id: str
    email: str
    password: Optional[str] = None



class UserResponse(BaseModel):
    name: str
    description: str
    dingtalk_id: str
    email: str
    password: str
    created_at: datetime

class UserListResponse(BaseModel):
    users: list[UserResponse] | None

class GroupBase(BaseModel):
    name: str
    description: str

class UserGroupBase(BaseModel):
    uname: str
    gnames: list[str]




class GroupResponse(BaseModel):
    name: str
    description: str

class GroupListResponse(BaseModel):
    groups: list[GroupResponse] | None

