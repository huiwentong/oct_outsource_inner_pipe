# -*- coding: utf-8 -*-
"""镜头 Blocking 收包，逻辑同 lay；对齐 oct_publish blk 接口，额外传 is_split_task"""
from behaviour.dispatch_behav.lay import Component as LayComponent


class Component(LayComponent):
    LABEL = 'Blocking'
    PRIMARY_TASK = 'blocking'

    def extra_input_form(self, task_name: str) -> dict:
        # 主任务以外（如 blocking_a）都是拆分任务，与 oct_publish 的强制规则一致
        return {'is_split_task': task_name != self.PRIMARY_TASK}
