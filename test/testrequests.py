import requests
from permissionmanager.core.user_manager import FTPUserManager
from logger.core import get_log



def test_requests():
    url = 'http://192.168.30.9:8000/delete_path_group'
    data = {
        'path': '/srv/ftp/oct/mk2/asset/dasheng',
        'group': 'tex',
        'rescursive': False,
        'inherit': False,
    }
    res = requests.delete(
        url=url,
        json=data
        # params={
        #     'uname': 'testa'
        # }
    )
    print(res.json())

if __name__ == '__main__':
    # test_requests()
    logger = get_log()

    logger.info(FTPUserManager.get_path_group('/var/lib/docker/volumes/outsource-pip_ftpdata/_data/oct/mk2/asset/dasheng'))