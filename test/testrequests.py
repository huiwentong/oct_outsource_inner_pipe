import requests

def test_requests():
    url = 'http://192.168.30.9:8000/create_user'
    data = {
        'name': 'testa',
        'description': '测试使用',
        'ding_id': '034822000124675411',
        'email': 'adsdasdasd',
        'password': '123456'
    }
    res = requests.post(
        url=url,
        json=data
        # params={
        #     'g_name': 'mod'
        # }
    )
    print(res.json())

def test_requests():
    url = 'http://192.168.30.9:8000/user_groups'
    data = {
        'uname': 'test',
        'gnames': ['mk2', 'tex'],
    }
    res = requests.get(
        url=url,
        # json=data
        params={
            'uname': 'testa'
        }
    )
    print(res.json())

if __name__ == '__main__':
    test_requests()