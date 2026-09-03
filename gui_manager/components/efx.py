from components.core import FieldSpec, StepComponent, register

@register
class EfxComponent(StepComponent):
    step = "efx"
    name = "特效"
    color = "#ec4899"
    order = 7
    fields = [
        FieldSpec(
            key="output",
            label="输出内容",
            kind="combo",
            options=["特效工程", "合成序列", "工程 + 合成序列"],
            default="工程 + 合成序列",
            help="选择本次需要打包发送的特效产出内容。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该实体的特效工程 / 合成数据
        return {"note": f"{project}/{entity} 特效环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 特效] {payload}")
