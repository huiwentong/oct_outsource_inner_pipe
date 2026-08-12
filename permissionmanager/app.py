from permissionmanager.start import start
from fastapi import FastAPI
from permissionmanager.core.user_manager import FTPUserManager
from permissionmanager.core import models
app = FastAPI()
start()

@app.get('/get_user', response_model=models.UserListResponse)
def get_user(user_name: str):

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
def get_group(g_name: str):

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
        users=ulist
    )

