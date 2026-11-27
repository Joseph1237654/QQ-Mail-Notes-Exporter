# QQNoteExporter

[![CI](https://github.com/Joseph1237654/QQ-Mail-Notes-Exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/Joseph1237654/QQ-Mail-Notes-Exporter/actions/workflows/ci.yml)

面向 Windows 的 QQ 邮箱记事本导出工具。通过用户手动登录的 QQ 邮箱会话，批量读取
记事本内容，并将每条笔记导出为独立、保留标题的 Word 文档。

当前版本：`v0.1.5`

中文界面名称：**QQ邮箱记事本导出器**

英文界面名称：**QQ Mail Notebook Exporter**

## 下载与安装

普通用户无需安装 Python。

| 文件 | 用途 |
| --- | --- |
| [QQNoteExporter-Setup-0.1.5.exe](release/QQNoteExporter-Setup-0.1.5.exe) | Windows 安装程序 |
| [QQNoteExporter-Portable-0.1.5.zip](release/QQNoteExporter-Portable-0.1.5.zip) | 免安装便携版 |
| [SHA256SUMS.txt](release/SHA256SUMS.txt) | 发布文件校验值 |
| [发布说明](release/README.md) | 0.1.5 更新、签名和隐私说明 |

安装版默认安装到当前用户目录，不需要管理员权限：

```text
%LOCALAPPDATA%\Programs\QQNoteExporter
```

便携版解压后双击 `QQNoteExporter.exe` 即可运行。

### 系统要求

- Windows 10 或 Windows 11，64 位
- Microsoft Edge
- 可访问 QQ 邮箱的网络环境

### SmartScreen 说明

当前发布文件使用本地自签名证书签名，并非 CA 颁发的受信任代码签名证书。Windows
SmartScreen 仍可能显示“未知发布者”。

可以校验下载文件：

```powershell
Get-FileHash .\QQNoteExporter-Setup-0.1.5.exe -Algorithm SHA256
```

校验结果应与 [SHA256SUMS.txt](release/SHA256SUMS.txt) 中的值一致。

## 功能

- 手动登录 QQ 邮箱，程序不接收或保存 QQ 密码。
- 使用持久化 Edge 浏览器配置复用登录会话。
- 分页读取记事本列表，并按笔记 ID 去重。
- 每条笔记生成一个独立 `.docx` 文件。
- 原始标题同时保留在文件名和 Word 一级标题中。
- 写入分类、创建时间、修改时间和 HTML 转换后的正文。
- 正文照片按原始图片字节嵌入，不重新压缩像素。
- 远程图片复用当前 QQ 邮箱登录态下载。
- 图片按 A4 版心等比缩放，不裁剪、不拉伸。
- 支持常见段落、标题、嵌套列表、引用、代码块、链接和简单表格。
- 单条失败隔离，一条笔记出错不会中止整批任务。
- 遇到接口频控 `ret=-20003` 时自动等待并降低请求速度。
- Word 先写临时文件，完成结构校验后再原子替换。
- 桌面界面支持简体中文和 English，语言设置会持久保存。
- 桌面界面提供登录、导出、进度、成功/失败计数、活动日志和设置。

## 桌面版使用

1. 启动 `QQNoteExporter.exe`。
2. 点击“登录 QQ 邮箱”。
3. 在弹出的 Edge 窗口中完成登录，并进入记事本。
4. 打开左下角设置，选择 Word 导出目录和界面语言。
5. 返回主界面，点击“开始导出”。
6. 在活动日志中查看成功、跳过和失败情况。

语言切换会立即应用到主窗口、设置窗口、提示框和常见运行错误。语言选择会在下次启动时
继续生效。

## 从源码运行

要求 Python 3.11 或更高版本。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
```

启动桌面版：

```powershell
qq-notebook-desktop
```

检查本地环境：

```powershell
qq-notebook-export doctor
```

## 命令行

登录 QQ 邮箱：

```powershell
qq-notebook-export login
```

请在弹出的 Edge 窗口中完成登录并进入记事本。程序会验证 `sid` 是否真正可用于记事本
接口，并显示当前可读取的笔记数量。

批量导出：

```powershell
qq-notebook-export export --output .\exports
```

常用参数：

```powershell
qq-notebook-export export --limit 5 --overwrite
qq-notebook-export export --delay 0.5
qq-notebook-export export --profile D:\qq-mail-profile
```

| 命令 | 作用 |
| --- | --- |
| `qq-notebook-export doctor` | 检查 Python、依赖、Edge 和目录配置 |
| `qq-notebook-export login` | 打开持久化 Edge 并保存登录态 |
| `qq-notebook-export export` | 读取记事本并逐条导出 Word |
| `qq-notebook-desktop` | 启动 Windows 桌面版 |

## 导出结果

```text
exports/
  项目周记__3012.docx
  无标题__3108.docx
  会议记录__3220.docx
```

文件命名规则：

```text
{清洗后的标题}__{笔记 ID}.docx
```

Windows 非法字符会被替换，同名笔记由笔记 ID 区分。空标题显示为“无标题”。

### 图片处理

- `data:` 图片在本地解码。
- HTTP/HTTPS 图片通过当前 Edge 登录会话获取。
- 图片原始字节默认直接写入 DOCX。
- 超大图片只调整 Word 显示尺寸，不修改源图片像素。
- JPEG 的异常 EXIF 导致 Word 库无法识别时，仅移除 APP1 元数据并补标准 JFIF 头。
- 图片下载或解析失败时，整条笔记会明确失败，不会静默替换为占位文字。

## 隐私与安全

- 程序不接收、不保存 QQ 账号密码或验证码。
- 登录由用户在 Microsoft Edge 中手动完成。
- 浏览器配置保存在：

```text
%LOCALAPPDATA%\QQNotebookExporter\browser-profile
```

- 导出文件只写入用户选择的本地目录。
- 发布包不包含用户笔记、DOCX、PDF、日志、Cookie、浏览器历史或 SQLite 数据库。
- 构建脚本会扫描发布目录和本机隐私路径标记，发现泄漏会终止发布。

## 常见问题

### 登录后仍提示登录态不可用

1. 重新执行登录。
2. 确认 Edge 窗口已经完成登录。
3. 确认已经进入 QQ 邮箱记事本页面。
4. 保持页面打开，等待程序检测并验证 `sid`。

### 遇到 `ret=-20003`

这是 QQ 邮箱接口的临时频控。程序会自动等待、重试并逐步提高后续请求间隔。不要将
`--delay` 设置得过低。

### 图片导致某条笔记失败

说明该笔记存在无法下载、无法识别或不受 Word 支持的图片。失败项会显示在活动日志和
命令行结果中，其余笔记仍会继续导出。

### Word 文件打不开

程序默认先写临时文件并校验 ZIP/DOCX 结构，再替换最终文件。若仍遇到问题，请删除对应
文件后重新导出，并保留活动日志中的错误信息。

## 项目结构

```text
src/qq_notebook_exporter/
  browser.py          # Playwright 持久化浏览器、接口请求和图片下载
  gateway.py          # QQ 记事本列表、正文、频控和重试
  models.py           # 领域模型
  filenames.py        # Windows 安全文件名
  docx_exporter.py    # HTML、列表、图片和 Word 结构渲染
  workflow.py         # 批量导出、失败隔离和统计
  cli.py              # 命令行入口
  desktop/
    app.py            # PySide6 应用入口
    main_window.py    # 主窗口和任务状态
    settings_dialog.py
    i18n.py           # 中英文文案
    style.py          # 黑白灰界面样式
    workers.py        # 后台登录和导出线程
  resources/          # 应用 PNG/ICO 图标
packaging/            # PyInstaller、Inno Setup、签名和发布校验
scripts/              # 图标生成与 Windows 构建脚本
tests/                # 离线单元测试与夹具
docs/                 # 架构、打包和迭代路线
release/              # 安装包、便携版、校验值和发布说明
```

## 开发与测试

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,gui]"
ruff check .
pytest
```

CI 会在 Windows 上使用 Python 3.11、3.12 和 3.13 运行静态检查和全量测试。

## Windows 打包

安装构建依赖：

```powershell
python -m pip install -e ".[build,gui]"
```

构建便携目录：

```powershell
python scripts\build_windows.py
```

输出：

```text
dist\QQNoteExporter\
  QQNoteExporter.exe
  _internal\
```

安装 Inno Setup 6 后构建安装包：

```powershell
python scripts\build_windows.py --installer
```

安装包输出到 `release/`。更完整的签名、隐私扫描和发布检查见
[docs/packaging.md](docs/packaging.md)。

## 已知限制

- QQ 邮箱记事本接口没有公开稳定性承诺，字段变化时需要更新适配层。
- `sid` 失效后需要重新登录。
- 接口存在频率限制，默认请求间隔为 0.35 秒。
- 复杂富文本、嵌套表格和特殊版式仍可能需要后续增强。
- 当前桌面的任务取消和断点续传尚未实现。
- 自签名发布文件不会消除 SmartScreen 的未知发布者提示。

## 更多文档

- [架构设计](docs/architecture.md)
- [Windows 打包](docs/packaging.md)
- [迭代路线](docs/roadmap.md)
- [贡献指南](CONTRIBUTING.md)
- [许可证](LICENSE)
