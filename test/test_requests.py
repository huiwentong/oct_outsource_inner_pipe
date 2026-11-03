import requests
from pprint import pprint
import httpx
import pytest


@pytest.mark.asyncio
async def test_sse_stream():
    async with httpx.AsyncClient(base_url="http://192.168.20.211:8001") as client:
        async with client.stream("GET", "/api/items/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            lines = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    lines.append(line)
                if len(lines) >= 10:   # 拿到 2 条数据就停
                    break

            assert len(lines) >= 10

# def test_requests():
#     url = 'http://192.168.20.211:8000/get_path_group'
#     # data = {
#     #     'path': '/srv/ftp/oct/mk2/asset/dasheng',
#     #     'group': 'tex',
#     #     'rescursive': False,
#     #     'inherit': False,
#     # }
#     res = requests.get(
#         url=url,
#         # json=data
#         params={
#             '_path': '/srv/ftp/oct/mk2/asset/dasheng'
#         }
#     )
#     pprint(res.json()['detail'])

