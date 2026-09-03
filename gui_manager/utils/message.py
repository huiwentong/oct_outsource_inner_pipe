import requests
from datetime import datetime
import json




def send_simple_message(msg, title, user):
    uid = user['sg_dingtalk_id']
    url = 'http://192.168.20.217:8080/ding/msg/simple'

    mk_message = """
# 🚀 制片给您发布了新的外包数据
___
* ***通知信息:***  {message}
***
| 任务信息 | 查询结果 |
| :--- | :---: | 
| 资产 | {entitiy} | 
| 环节 | {step} |
| ftp位置 | {ftppath} |
***
`发送时间： {datetime_now}`
""".format(
           message=msg['message'],
           entitiy=msg['entitiy'],
           step=msg['step'],
           ftppath=msg['ftppath'],
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