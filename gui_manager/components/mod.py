from components.core import FieldSpec, StepComponent, register
@register
class ModComponent(StepComponent):
    step = "mod"
    name = "模型"
    color = "#3b82f6"
    order = 1
    fields = [
        FieldSpec(
            key="scope",
            label="打包内容",
            kind="combo",
            options=["模型 + 贴图", "仅模型(.mb/.ma)", "模型 + 贴图 + 工程"],
            default="模型 + 贴图",
            help="选择本次需要打包发送的文件范围。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该实体在模型环节最新的发布版本等数据
        return {"note": f"{project}/{entity} 模型环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 模型] {payload}")
