import asyncio
import importlib
from behaviour.utils.queueevent import Event
import traceback
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from dataclasses import asdict
from queue import Empty
import json


executor = ThreadPoolExecutor(max_workers=10)


class Pipeline():

    def __init__(self, loop, logger, queue:asyncio.Queue) -> None:
        self.loop = loop
        self.queue = queue
        self.state_file = Path(os.environ['STATE_DIR']) / 'state.json'
        self.logger = logger
        self._stop = asyncio.Event()

    async def run(self):
        self.logger.info("behaviour 事件流水线 pipline启动")
        if self.state_file.exists():
            with self.state_file.open('r') as f:
                event_list = json.load(f)
            for event in event_list:
                self.queue.put_nowait(
                    Event(**event)
                )
            self.state_file.unlink()
            

        while not self._stop.is_set():
            try:
                ev = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                ev = None
            if ev is not None:
                self.logger.info(
                    "behaviour pipeline 捕获到事件 %s，队列剩余 %d",
                    ev.summary(),
                    self.queue.qsize(),
                )
                await self._process_event(ev)

        await self._flush_all()
        


    async def _process_event(self, event: Event):
        step = event.step
        try:
            module = importlib.import_module(f'behaviour.dispatch_behav.{step}')
            component = module.Component(event)
            await self.loop.run_in_executor(executor, component.process)
        except Exception:
            self.queue.put_nowait(event)
            self.logger.error(f'导入模块{step}时出现错误')
            self.logger.error(traceback.format_exc())
            await self._flush_all()
            raise RuntimeError('出现了错误，阻塞所有进程')




    async def _flush_all(self):
        if not self.state_file.exists():
            self.state_file.touch()
        with self.state_file.open('r') as f:
            event_list = json.load(f)
        event_list = event_list or []
        while True:
            try:
                event = self.queue.get_nowait()
                event_list.append(asdict(event))
            except Empty:
                break
        with self.state_file.open('w') as f:
            json.dump(event_list, f, indent=4)

    

    def stop(self):
        self._stop.set()