import requests
from datetime import datetime
import json


def pack_collection_text(msg):
    """发包通知正文, 钉钉和邮件共用. 用标题+列表不用表格, 纯文本邮件里也能读.

    msg['changes'] 是 Database.vendor_entity_changes 的结果; 为 None (判断失败) 时退回列出全部发包资产.
    """
    changes = msg.get('changes')
    if changes is None:
        assets = f"**发包资产**：{msg['rely_assets']}"
    else:
        names = lambda status: ', '.join(sorted(k for k, v in changes.items() if v['status'] == status)) or '无'
        unchanged = sum(v['status'] == '未变' for v in changes.values())
        assets = f"**本次发包**：共 {len(changes)} 个资产/镜头\n\n**新增**：{names('新增')}\n\n**有更新**：{names('有更新')}\n\n**未变**：共 {unchanged} 个资产/镜头"
    description = '\n'.join(f'- {line}' for line in msg['description'].splitlines() if line.strip()) or '无'

    return f"""# 🚀 十月文化给您更新了资产/环节物料！

物料已发送成功，请进入ftp客户端进行查看！

{assets}

**发包环节**：{msg['rely_steps']}

**备注信息**：

{description}

**发包人员**：{msg['user']}

发送时间： {datetime.now():%Y-%m-%d %H:%M:%S}
"""


def send_pack_collection_message(msg, user):
    uid = user
    url = 'http://192.168.20.217:8080/ding/msg/simple'

    post_data = {
        'title': '来自十月的发包通知' ,
        'text': pack_collection_text(msg)
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



def send_email_with_alibaba(msg=None, user={}):
    url = 'http://192.168.20.217:8080/ding/msg/email'

    mk_message = {
        'content': str(msg),
        'subject': '十月文化-邮件通知',
        'summary': '用于外包方的重要信息提醒'

    }
    post_data = {
        'msg': mk_message ,
        'user': user
    }
    print(post_data)
    ret = requests.post(
        url=url,
        data=json.dumps(post_data)
    )
    ret.raise_for_status()
    return ret.json()



if __name__ == "__main__":
    send_email_with_alibaba()