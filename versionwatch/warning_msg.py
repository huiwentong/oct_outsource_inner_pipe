import requests
import traceback
import json

def send_warning_message(msg):
    try_times = 0
    errors = ''

    while try_times < 5:

        try:

            url = 'http://192.168.20.217:8080/ding/msg/simple2'

            mk_message = f"""
# 💥💥 外包服务框架中的behaviour模块出现了错误
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