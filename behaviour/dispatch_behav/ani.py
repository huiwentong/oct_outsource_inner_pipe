# -*- coding: utf-8 -*-
"""镜头 Animation 收包，继承 blk，只改主任务名"""
from behaviour.dispatch_behav.blk import Component as BlkComponent


class Component(BlkComponent):
    LABEL = 'Animation'
    PRIMARY_TASK = 'animation'
