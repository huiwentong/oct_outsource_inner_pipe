import requests


def test_requests():
    url = 'http://192.168.30.9:8000/create_user'
    data = {
        'name': 'heguang',
        'description': '外包商: 和光同尘',
        'ding_id': 'asdasdw213sdd12',
        'email': 'heguang@qq.com',
        'password': '123456'
    }
    res = requests.post(
        url=url,
        json=data
        # params={
        #     'uname': 'testa'
        # }
    )
    print(res.json())

if __name__ == '__main__':
    test_requests()