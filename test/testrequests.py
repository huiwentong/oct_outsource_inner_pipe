import requests


def test_requests():
    url = 'http://192.168.30.9:8000/add_u2g'
    data = {
        'uname': 'yuanli',
        'gnames': ['mko','mk2', 'dasheng', 'mod', 'tex', 's010010'],
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