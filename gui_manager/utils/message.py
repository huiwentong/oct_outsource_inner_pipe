import requests
from datetime import datetime
import json

token = None

def send_pack_collection_message(msg, user):
    uid = user
    url = 'http://192.168.20.217:8080/ding/msg/simple'

    mk_message = """
# 🚀 十月文化给您更新了资产/环节物料！
___
物料已发送成功，请进入ftp客户端进行查看！
***
| 信息 | 内容 |
| :--- | :---: | 
| 备注信息 | {description} | 
| 发包资产 | {rely_assets} | 
| 发包环节 | {rely_steps} | 
| 发包人员 | {user} | 
***
`发送时间： {datetime_now}`
""".format(
            description=msg['description'],
            rely_assets=msg['rely_assets'],
            rely_steps=msg['rely_steps'],
            user=msg['user'],
            datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    post_data = {
        'title': '来自十月的发包通知' ,
        'text': mk_message
    }

    ret = requests.post(
        url=url,
        params={'user_id': uid},
        data=json.dumps(post_data)
    )

    ret.raise_for_status()
    return ret.json()


def send_simple_message(msg, title, user):
    uid = user
    url = 'http://192.168.20.217:8080/ding/msg/simple'

    mk_message = """
# 🚀 管理员给您创建了账户！
___
ftp地址和密码为重要信息，请妥善保管！
***
| 账户信息 | 值 |
| :--- | :---: | 
| 用户名称 | {username} | 
| 用户密码 | {password} |
| 用户id | {user_id} |
| ftp端口 | {frp_port} |
| ftp地址 | {frp_address} |
| 用户目录 | {frp_home} |
***
`发送时间： {datetime_now}`
""".format(
           username=msg['username'],
           password=msg['password'],
           user_id=msg['user_id'],
           frp_port=msg['frp_port'],
           frp_address=msg['frp_address'],
           frp_home=msg['frp_home'],
           datetime_now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    post_data = {
        'title': title ,
        'text': mk_message
    }

    ret = requests.post(
        url=url,
        params={'user_id': uid},
        data=json.dumps(post_data)
    )

    ret.raise_for_status()
    return ret.json()

def get_token_from_alibaba():
    global token
    if token:return token
    url = 'https://alimail-cn.aliyuncs.com/oauth2/v2.0/token'
    ret = requests.post(
        url=url,
        data={
            'grant_type': 'client_credentials',
            'client_id': 'QA0gvNcVVTniRSXl',
            'client_secret': '50cHQryqi6Ma0daZUFoHRwzsm8Wmw0eF94p4MCicn2l3sPKMjxc4bE1yo8dngnsG'
        }
    )
    token = ret.json()['access_token']
    return token


def send_email_with_alibaba(msg=None, user={}):
    global token
    token = get_token_from_alibaba()
    email = 'huiwentong@octmedia.com'  # 例如：test@yourcompany.com
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload={
        "message": {
            "subject": "测试邮件",
            "summary": "测试邮件",
            "priority": "PRY_HIGH",
            "from": {
                "email": email,
                "name": "十月文化"
            },
            "body": {
                "bodyText": msg,
                "bodyHtml": f"<p>{msg}</p>"
            },
            "toRecipients": [
                {
                    "email": user['email'],
                    "name": user['name']
                }
            ]
        }
    }
    url = f'https://alimail-cn.aliyuncs.com/v2/users/{email}/messages'
    ret = requests.post(
        url=url,
        headers=headers,
        json=payload
    )
    ret.raise_for_status()

    id = ret.json()['message']['id']

    send_url = f'https://alimail-cn.aliyuncs.com/v2/users/{email}/messages/{id}/send'
    ret = requests.post(
        send_url,
        headers=headers,
        json={"saveToSentItems": True},
    )

    print(ret.status_code, ret.text)
    ret.raise_for_status()



if __name__ == "__main__":
    send_email_with_alibaba()