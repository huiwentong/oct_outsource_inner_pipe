import requests
from datetime import datetime
import json




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