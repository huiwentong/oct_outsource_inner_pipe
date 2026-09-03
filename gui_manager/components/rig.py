from components.core import FieldSpec, StepComponent, register
@register
class RigComponent(StepComponent):
    step = "rig"
    name = "绑定"
    color = "#0ea5e9"
    order = 3
    fields = [
        FieldSpec(
            key="with_test",
            label="包含绑定测试文件",
            kind="check",
            default=True,
            help="勾选后会把测试动画 / 测试场景一并打包。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该实体的绑定文件 / 测试文件数据
        return {"note": f"{project}/{entity} 绑定环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 绑定] {payload}")
