from components.core import FieldSpec, StepComponent, register
@register
class CfxComponent(StepComponent):
    step = "cfx"
    name = "特效解算"
    color = "#ef4444"
    order = 6
    fields = [
        FieldSpec(
            key="cache_type",
            label="解算缓存格式",
            kind="combo",
            options=["Alembic(.abc)", "USD(.usd)", "缓存 + 源工程"],
            default="Alembic(.abc)",
            help="选择需要打包的解算缓存格式。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该实体的解算缓存 / 源工程数据
        return {"note": f"{project}/{entity} 特效解算环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 特效解算] {payload}")
