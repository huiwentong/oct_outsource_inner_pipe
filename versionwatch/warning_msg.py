import requests
import traceback
import json
from datetime import datetime

def send_warning_message(msg):
    try_times = 0
    errors = ''

    while try_times < 5:

        try:

            url = 'http://192.168.20.217:8080/ding/msg/simple2'

            mk_message = f"""
# 💥💥 外包服务框架中的versionwatch模块出现了错误
___
    {msg}
        """
            post_data = {
                'title': '外包服务框架出现问题，需要处理',
                'text': mk_message
            }

            ret = requests.post(
                url=url,
                data=json.dumps(post_data)
            )

            ret.raise_for_status()
            return ret.json()
        except:
            try_times += 1
            errors += f'error time {try_times}: {traceback.format_exc()}\n'

    raise RuntimeError(errors)



MAX_ITEMS_PER_SECTION = 50


def _format_error_list(errors: list[str]) -> str:
    """把 error 列表格式化成 Markdown 列表"""
    if not errors:
        return '无'
    lines = [f'- {e}' for e in errors[:MAX_ITEMS_PER_SECTION]]
    if len(errors) > MAX_ITEMS_PER_SECTION:
        lines.append(f'- ...（共 {len(errors)} 条，已省略 {len(errors) - MAX_ITEMS_PER_SECTION} 条）')
    return '\n'.join(lines)


def _format_update_list(items: list[str]) -> str:
    """
    把 need_to_update 列表格式化。
    每项形如：
      4 段：project|entity_type|entity|step
      5 段：project|entity_type|entity|step|rig_folder
    """
    if not items:
        return '无'

    lines = []
    for raw in items[:MAX_ITEMS_PER_SECTION]:
        parts = raw.split('|')
        if len(parts) == 5:
            project, entity_type, entity, step, rig_folder = parts
            lines.append(f'- `{project}` / {entity_type} / {entity} / **{step}** / {rig_folder}')
        elif len(parts) == 4:
            project, entity_type, entity, step = parts
            lines.append(f'- `{project}` / {entity_type} / {entity} / **{step}**')
        else:
            # 不符合预期格式，原样展示，避免丢信息
            lines.append(f'- {raw}')

    if len(items) > MAX_ITEMS_PER_SECTION:
        lines.append(f'- ...（共 {len(items)} 条，已省略 {len(items) - MAX_ITEMS_PER_SECTION} 条）')
    return '\n'.join(lines)


def send_simple_message(msg, title, user):
    """
    :param msg:   dict，包含 {'errors': [...], 'need_to_update': [...]}
                  也兼容直接传两个 list 的旧调用（见下方兼容逻辑）
    :param title: 消息标题
    :param user:  钉钉 user_id
    """
    uid = user
    url = 'http://192.168.20.217:8080/ding/msg/simple'

    # ---- 兼容两种入参 ----
    if isinstance(msg, dict):
        errors = msg.get('errors') or []
        need_to_update = msg.get('need_to_update') or []
    elif isinstance(msg, (list, tuple)) and len(msg) == 2:
        errors, need_to_update = msg
    else:
        errors, need_to_update = [], []

    mk_message = f"""
# 🤖🤖🤖 ftp每日扫盘通知
___
***
`发送时间： {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`

***

## ❌ 扫盘异常（{len(errors)} 条）
{_format_error_list(errors)}

***

## 🔄 需要更新（{len(need_to_update)} 条）
{_format_update_list(need_to_update)}
"""

    post_data = {
        'title': title,
        'text': mk_message,
    }

    ret = requests.post(
        url=url,
        params={'user_id': uid},
        data=json.dumps(post_data, ensure_ascii=False),  
        timeout=10,                                      
    )
    ret.raise_for_status()
    return ret.json()

if __name__ == '__main__':
    send_simple_message({}, '每日扫盘通知','034822000124675411')