from behaviour.dispatch_behav.core import StepComponent
from behaviour.utils.queueevent import Event


class Component(StepComponent):
    def __init__(self, event: Event) -> None:
        super().__init__(event)


    def check_extra(self):
        return super().check_extra()


    def publish_to_ddline(self):
        return super().publish_to_ddline()