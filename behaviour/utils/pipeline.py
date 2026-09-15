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
            event_list = self._safe_load_state()
            for event in event_list:
                self.queue.put_nowait(
                    Event(**event)
                )
            try:
                self.state_file.unlink(missing_ok=True)
                self.logger.info("已加载 %d 个历史事件并清理状态文件", len(event_list))
            except OSError as e:
                self.logger.error("删除状态文件失败: %s", e)
            

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
        
    def _safe_load_state(self) -> list[dict]:
        """安全加载状态文件，处理空文件和JSON格式错误"""
        try:
            size = self.state_file.stat().st_size
        except OSError:
            return []

        # ✅ 核心修复：空文件直接返回默认值
        if size == 0:
            self.logger.warning("状态文件为空，跳过加载: %s", self.state_file)
            return []

        try:
            with self.state_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error("状态文件JSON解析失败: %s，内容可能已损坏", e)
            # 备份损坏文件以便事后排查
            backup = self.state_file.with_suffix('.json.corrupt')
            try:
                self.state_file.rename(backup)
                self.logger.info("已备份损坏的状态文件至: %s", backup)
            except OSError:
                pass
            return []
        except OSError as e:
            self.logger.error("读取状态文件失败: %s", e)
            return []

        if not isinstance(data, list):
            self.logger.error("状态文件格式错误，期望list但得到 %s", type(data).__name__)
            return []

        return data

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
        event_list = self._safe_load_state()
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