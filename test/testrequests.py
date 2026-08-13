import requests

def test_requests():
    url = 'http://192.168.30.9:8000/get_group'
    res = requests.get(
        url=url,
        params={
            'g_name': 'mod'
        }
    )
    print(res.json())

if __name__ == '__main__':
    test_requests()