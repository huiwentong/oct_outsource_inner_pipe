from fastapi import FastAPI, HTTPException, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from collections.abc import AsyncIterable
from . import logger
import asyncio
from contextlib import asynccontextmanager
from behaviour.utils.pipeline import Pipeline
from behaviour.utils.queueevent import make_event
from dataclasses import asdict

import logging


class HealthFilter(logging.Filter):
    def filter(self, record):
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthFilter())

queue = asyncio.Queue()

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    pip = Pipeline(loop, logger=logger, queue=queue)
    task = loop.create_task(pip.run())
    logger.info(f'behaviour pipeline 启动！{id(queue)}')
    try:
        yield
    finally:
        pip.stop()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("behaviour pipeline 异常退出")


app = FastAPI(lifespan=lifespan)



@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/observe_manifest")
def observe(manifest_path: str, vendor:str):
    try:
        manifest_path = '/srv/ftp/' + manifest_path


        event = make_event(manifest_path=manifest_path, vendor=vendor)

    except ValueError as e:
        logger.warning(
            "创建 Event 失败，manifest=%s，原因：%s",
            manifest_path,
            e,
        )
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception:
        logger.exception(
            "创建 Event 时发生未知错误，manifest=%s",
            manifest_path,
        )
        raise HTTPException(
            status_code=500,
            detail="创建事件失败",
        )

    queue.put_nowait(event)

    return {
        "status": "queued",
        "event": asdict(event),
    }


async def get_new_items(last_id: int):
    await asyncio.sleep(2)
    return [
        {'id':123, 'name':'test'},
        {'id':321, 'name':'test2'}
    ]


@app.get("/items/stream", response_class=EventSourceResponse)
async def stream_items() -> AsyncIterable[ServerSentEvent]:
    last_id = 0
    while True:
        items = await get_new_items(last_id)

        for item in items:
            last_id = item['id']
            yield ServerSentEvent(
                data={"id": item['id'], "name": item['name']},
                event="item_update",
                id=str(item['id'])
            )
        
        if not items:
            await asyncio.sleep(60)