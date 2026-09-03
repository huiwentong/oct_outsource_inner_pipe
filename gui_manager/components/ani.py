from components.core import FieldSpec, StepComponent, register
@register
class AniComponent(StepComponent):
    step = "ani"
    name = "动画"
    color = "#f59e0b"
    order = 5
    fields = [
        FieldSpec(
            key="with_playblast",
            label="包含 Playblast 预览",
            kind="check",
            default=True,
            help="勾选后会把预览小样一起打包发送。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该镜头在动画环节的任务版本数据
        return {"note": f"{project}/{entity} 动画环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 动画] {payload}")
