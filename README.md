# QQNoteExporter

面向 Windows 的 QQ 邮箱记事本导出工具，用于将笔记逐条导出为 Word 文档。每条笔记
生成一个独立的 `.docx` 文件，原始标题同时保留在文件名和文档一级标题中。

当前版本是首个基础架构版本，包含：

- 手动登录 QQ 邮箱并使用持久化 Edge 浏览器会话。
- 在已登录页面上下文内分页读取记事本列表和正文。
- 一条笔记一个 Word 文件，标题、分类、时间和正文分层写入，照片按原始字节嵌入。
- 单条失败隔离，批量导出不会因一条笔记异常而全部中止。
- 桌面版使用独立应用图标，并保留多尺寸图标资源用于后续安装包。
- 桌面界面支持简体中文与 English 切换，语言选择会持久保存。
- 单元测试、Windows CI、PR 模板和后续迭代路线。

最终交付形态是 Windows 桌面软件：用户通过图形界面完成登录、选择导出目录、查看导出
进度和失败项；核心导出层继续复用当前架构，最后一个阶段再通过 PyInstaller 打包成无需
安装 Python 的 `.exe`。

## 安全边界

- 程序不接收、不保存 QQ 密码。
- 登录由用户在打开的 Edge 窗口中手动完成。
- 浏览器配置保存在本机用户目录，不会写入 Git 仓库。
- 导出文件只保存在本地指定目录。

## 安装

要求 Windows 10/11、Python 3.11 或更高版本、Microsoft Edge。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
```

默认使用系统已安装的 Microsoft Edge。若改用 Playwright 自带的 Chromium：

```powershell
python -m playwright install chromium
qq-notebook-export doctor --channel chromium
```

## 使用

先检查本地环境：

```powershell
qq-notebook-export doctor
```

打开浏览器并手动登录：

```powershell
qq-notebook-export login
```

请在弹出的 Edge 窗口中完成 QQ 邮箱登录，并进入记事本。工具检测到 `sid` 后还会调用
记事本接口验证登录态是否真实可用，并显示首屏可读取的笔记数量。

批量导出：

```powershell
qq-notebook-export export --output .\exports
```

常用参数：

```powershell
qq-notebook-export export --limit 5 --overwrite
qq-notebook-export export --delay 0.35
qq-notebook-export export --profile D:\qq-mail-profile
```

启动 Windows 桌面版：

```powershell
qq-notebook-desktop
```

桌面版使用黑白灰极简界面，提供登录、导出进度、成功/失败计数和活动日志。导出路径、
界面语言与版本信息集中在左下角“设置”入口中。

导出结果示例：

```text
exports/
  项目周记__3012.docx
  无标题__3108.docx
```

每个文件包含：

1. 原始标题作为一级标题。
2. 分类、创建时间和修改时间。
3. QQ 记事本 HTML 转换后的正文。

正文中的照片默认直接嵌入原始图片数据；页面只调整显示尺寸，不裁剪、不重新编码像素。
若 Python-DOCX 无法解析 JPEG 中的异常 EXIF，则会移除 APP1 元数据并补标准 JFIF 头，
图片扫描数据保持不变。需要登录态的远程图片通过同一个 Edge 会话获取，获取失败时该条
笔记会明确报错，不会静默替换成“[图片]”。

## 命令

| 命令 | 作用 |
| --- | --- |
| `doctor` | 检查 Python、依赖、Edge 和目录配置 |
| `login` | 打开持久化浏览器并等待登录态 |
| `export` | 读取记事本并逐条导出 Word |

## 项目结构

```text
src/qq_notebook_exporter/
  browser.py         # Playwright 持久化浏览器会话
  gateway.py         # QQ 记事本 API 适配器
  models.py          # 领域模型
  filenames.py       # Windows 安全文件名
  docx_exporter.py   # HTML 到 Word 渲染
  workflow.py        # 批量导出编排
  cli.py             # 命令行入口
  desktop/            # PySide6 桌面界面与后台任务
  resources/          # 应用 PNG/ICO 图标
scripts/              # 图标生成等开发辅助脚本
tests/               # 离线单元测试
docs/                # 架构与 PR 路线
```

详细设计见 [docs/architecture.md](docs/architecture.md)，逐步 PR 计划见
[docs/roadmap.md](docs/roadmap.md)。

## 已知限制

- QQ 邮箱接口没有公开稳定性承诺，接口字段变化时需要在 `gateway.py` 中更新适配。
- `sid` 失效后需要重新执行 `login`。
- 接口有频率限制，默认逐请求间隔为 0.35 秒；触发 `ret=-20003` 时会自动等待并
  逐级降低请求速度，调低 `--delay` 仍可能增加限流风险。
- Word 转换覆盖常见段落、标题、列表、引用、代码块、简单表格和图片；复杂富文本会在
  后续 PR 中增强。
- 发布文件使用本地自签名证书，SmartScreen 仍可能提示未知发布者；正式发行需要 CA
  代码签名证书。

## Windows 打包

打包使用 PyInstaller 和 Inno Setup，详细步骤与隐私边界见
[docs/packaging.md](docs/packaging.md)。构建只会收集程序代码和运行资源；
`exports/`、浏览器配置、日志、DOCX、PDF 和测试产物不会进入软件包。

```powershell
python -m pip install -e ".[build,gui]"
python scripts\build_windows.py
```

便携版输出到 `dist/QQNoteExporter`。使用 `--installer` 参数并安装 Inno Setup 6
后，可生成 `release/QQNoteExporter-Setup-*.exe`。
