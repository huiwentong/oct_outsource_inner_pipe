from permissionmanager.start import start
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from typing import Optional
from permissionmanager.core.user_manager import FTPUserManager
from permissionmanager.core import models
import traceback

import secrets
import string
from logger.core import get_log

logger = get_log()

def gen_password():
    chars = string.ascii_letters + string.digits
    password = ''.join(
        secrets.choice(chars)
        for _ in range(6)
    )

    return password

app = FastAPI()
start()

@app.get('/get_user', response_model=models.UserListResponse)
def get_user(user_name: Optional[str] = None):

    users = FTPUserManager.get_user(user_name)
    print(users)
    ulist = []
    for u in users:
        if not u: continue
        ulist.append(
            models.UserResponse(
                name=u['name'],
                description=u['description'],
                dingtalk_id=u['dingtalk_id'],
                email=u['email'],
                password=u['password'],
                created_at=u['created_at']
            )
        )

    return models.UserListResponse(
        users=ulist
    )

@app.get('/get_group', response_model=models.GroupListResponse)
def get_group(g_name: Optional[str] = None):

    gs = FTPUserManager.get_group(g_name)
    print(gs)
    ulist = []
    for u in gs:
        if not u: continue
        ulist.append(
            models.GroupResponse(
                name=u['name'],
                description=u['description'],
            )
        )

    return models.GroupListResponse(
        groups=ulist
    )



@app.post('/create_group')
def create_group(group:models.GroupBase):
    try:
        ret_group = FTPUserManager.create_group(
            groupname=group.name,
            description=group.description
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )

    if ret_group:
        return {
            "message": "group created successfully",
            "groupname": group.name,
            "groupid": ret_group['id'],
        }
    else:
        return {
            "message": "group already exists!",
            "groupname": group.name,
        }


@app.post('/create_user')
def create_user(user: models.FtpUserBase):
    try:

        if not user.password:
            password = gen_password()
        else:
            password = user.password

        ret_user = FTPUserManager.create_user(
            username=user.name,
            password=password,
            home=f"/srv/ftp/{user.name}",
            ding=user.ding_id,
            email=user.email,
            description=user.description
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )

    if ret_user:
        return {
            "message": "User created successfully",
            "username": user.name,
            "userid": ret_user['id'],
            "userpswd": ret_user['password'],
        }
    else:
        return {
            "message": "User already exists!",
            "username": user.name,
        }


@app.post('/add_u2g')
def add_u2g(u2g:models.UserGroupBase):
    try:
        FTPUserManager.set_user_group(
            username=u2g.uname,
            groupnames=u2g.gnames
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )

    ugroups = FTPUserManager.get_user_group(username=u2g.uname)
    return {
        "message": f"User {u2g.uname} successfully append to group!",
        "usergroups": ugroups
        }


@app.get('/user_groups')
def user_groups(uname:str):
    try:
        ugroups = FTPUserManager.get_user_group(username=uname)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )
    
    return {
        "message": f"User {uname} groups",
        "usergroups": ugroups
        }

@app.delete('/users/{uname}', status_code=204)
def dele_user(uname: str):
    try:
        FTPUserManager.delete_user(username=uname)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        logger.error(f'delete user {uname} failed')
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )
    return Response()

@app.delete('/groups/{gname}', status_code=204)
def dele_group(gname: str):
    try:
        FTPUserManager.delete_group(groupname=gname)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)+traceback.format_exc()
        )

    except Exception:
        logger.error(f'delete group {gname} failed')
        raise HTTPException(
            status_code=500,
            detail="Internal server error"+traceback.format_exc()
        )
    return Response()