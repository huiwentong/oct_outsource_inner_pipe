from components.core import FieldSpec, StepComponent, register
@register
class LayComponent(StepComponent):
    step = "lay"
    name = "Layout"
    color = "#14b8a6"
    order = 4
    fields = [
        FieldSpec(
            key="range",
            label="镜头帧范围",
            kind="text",
            default="1001-1100",
            placeholder="例如 1001-1100",
            help="填写本次需要抓包的镜头帧范围。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该镜头在 layout 环节的任务版本数据
        return {"range": "1001-1100", "note": f"{project}/{entity} layout 环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - Layout] {payload}")
