from components.core import FieldSpec, StepComponent, register
@register
class TexComponent(StepComponent):
    step = "tex"
    name = "材质"
    color = "#8b5cf6"
    order = 2
    fields = [
        FieldSpec(
            key="resolution",
            label="贴图分辨率",
            kind="combo",
            options=["2K", "4K", "8K", "全部"],
            default="4K",
            help="选择需要打包发送的贴图分辨率。",
        ),
        FieldSpec(
            key="note",
            label="备注",
            kind="text",
            placeholder="选填，例如给外包方的补充说明",
        ),
    ]

    def mock_defaults(self, entity: str, project: str) -> dict:
        # TODO(后续补充): 查询该实体在材质环节的贴图 / 源文件数据
        return {"note": f"{project}/{entity} 材质环节 mock 数据"}

    def collect(self, payload: dict) -> None:
        print(f"[mock抓包 - 材质] {payload}")
