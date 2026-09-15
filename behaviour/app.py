from fastapi import FastAPI, HTTPException, Response
from . import logger
import asyncio
from contextlib import asynccontextmanager
from behaviour.utils.pipeline import Pipeline
from behaviour.utils.queueevent import make_event
from dataclasses import asdict


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