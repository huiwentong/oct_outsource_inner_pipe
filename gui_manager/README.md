# gui_manager

基于 Python + PySide6 的两个独立 GUI 工具，服务于外包收发包流程。

## 工具

| 工具 | 入口 | 用途 |
| --- | --- | --- |
| collector | `python collector.py` | 制片选择项目 / 资产 / 环节后，把制作文件抓包并发送给外包方 |
| usermanager | `python usermanager.py` | 在数据库与 FTP 中新增外包方用户、生成密码并赋予权限 |

> 当前两个工具的界面数据与后台逻辑均为 mock，真实查询 / 抓包 / 入库逻辑按 `project.md` 后续补充。

## 目录结构

```text
collector.py / usermanager.py   # 两个 GUI 的启动入口
server_config.yml               # 服务器基础配置（db / ftp / 权限服务）
components/                     # collector 按环节提供的能力模块
  core.py                       # 环节注册表 + StepComponent / FieldSpec 基类
  mod.py tex.py rig.py lay.py ani.py cfx.py efx.py
ui/                             # PySide6 界面代码
  collector/                    # collector 主窗口与 mock 数据
  usermanager/                  # usermanager 主窗口与 mock 服务层
  style.py                      # 两个 GUI 共用的 QSS 样式
utils/                          # 两个 GUI 共用的基础逻辑
  config.py                     # 读取 server_config.yml
  db.py                         # PostgreSQL 访问
  ftp.py                        # FTP 上传
  permissionmanager.py          # 调用 permissionmanager 服务
  message.py / hashing.py
```

## 环境

```bash
uv sync          # 安装依赖（见 pyproject.toml）
python collector.py     # 或 uv run collector.py
python usermanager.py
```

## 后续接入点

- collector：替换 `ui/collector/mock_data.py` 的实体 / 外包方数据；在每个 `components/*.py` 的 `mock_defaults` / `collect` 中补充真实查询与抓包逻辑。
- usermanager：替换 `ui/usermanager/services.py` 的权限校验与创建逻辑，可直接使用 `utils/permissionmanager.py` / `utils/db.py`。
