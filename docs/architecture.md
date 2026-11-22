# 架构设计

## 目标

在 Windows 上使用 Python，复用用户已登录的 QQ 邮箱浏览器会话，分页读取记事本，
再逐条生成保留标题的 Word 文档。

## 数据流

```text
CLI / PySide6 桌面界面
  -> BrowserSession
       -> 持久化 Edge 用户目录
       -> 在 qq.com 页面上下文执行 fetch
       -> 按登录态获取笔记图片原始字节
  -> QQMailNotebookGateway
       -> /webnote/list
       -> /webnote/read
  -> ExportService
       -> DocxExporter
       -> Windows 文件系统
```

`BrowserSession` 是唯一接触 Playwright 的模块。`QQMailNotebookGateway` 只依赖一个
很小的 JSON 传输协议，因此接口解析和分页逻辑可以用伪响应离线测试。`ExportService`
只依赖 `NoteSource` 和 `DocxExporter`，不关心 QQ 登录细节。

CLI 和桌面界面都必须调用同一套应用服务，禁止在 GUI 代码中直接调用 Playwright 或
QQ 接口。这样可以用离线测试稳定核心逻辑，同时让 Windows 桌面层只处理窗口、任务状态、
进度和用户选择。

## 模块边界

| 模块 | 职责 | 不负责 |
| --- | --- | --- |
| `browser.py` | 启动 Edge、保存登录状态、页面内请求和图片下载 | 解析业务数据 |
| `gateway.py` | QQ 记事本接口、分页、字段兼容 | 文件输出 |
| `models.py` | 笔记领域模型 | 网络和文件系统 |
| `filenames.py` | Windows 文件名清洗 | 写文件 |
| `docx_exporter.py` | Word 文档渲染、图片原字节嵌入和版心适配 | 登录态和网络传输 |
| `workflow.py` | 批量执行、失败隔离、统计 | 用户界面 |
| `cli.py` | 参数解析、进度和错误展示 | 网络细节 |
| `desktop/` | Windows 窗口、后台任务、进度、目录选择 | 网络协议和 Word 细节 |

## 登录态

登录命令打开可见的 Edge 窗口，用户手动登录。浏览器配置写入：

```text
%LOCALAPPDATA%\QQNotebookExporter\browser-profile
```

程序从 Cookie 或当前页面 URL 查找 `sid`。导出命令不读取密码，也不把登录信息写入
项目目录。请求在 `wx.mail.qq.com` 页面上下文内通过 `fetch` 发出，以复用页面登录态。

## Word 输出规则

- 一个 `NoteSummary` 对应一个文件。
- 文件名：`{清洗后的标题}__{笔记 ID}.docx`。
- 文档一级标题：原始标题；空标题使用 `无标题`。
- 文档属性标题：与一级标题一致。
- 同名的不同笔记由笔记 ID 区分。
- 默认跳过已存在文件，`--overwrite` 时覆盖。
- `<img>` 的原始图片字节直接写入 DOCX，不重新编码或压缩。
- `data:` 图片在本地解码；远程图片由 `BrowserSession` 复用当前登录态下载。
- 显示尺寸只按 A4 版心等比缩放，不裁切；图片下载或格式识别失败时整条笔记失败，
  不使用占位文字静默替代。
- 应用图标位于 `resources/app.png` 和 `resources/app.ico`，由
  `scripts/generate_app_icon.py` 生成。

## 错误策略

- 登录态失效：抛出 `AuthenticationRequiredError`，提示重新执行 `login`。
- 单条笔记读取失败：记录失败并继续下一条。
- 单个文档写入失败：记录失败并继续。
- 接口返回非 JSON 或字段异常：抛出明确的 API 错误。
- 接口返回 `ret=-20003`：视为临时频控，按指数退避后重试。

## 测试策略

默认测试完全离线：

- 用固定 JSON 伪响应验证列表分页和正文字段兼容。
- 用分页、重复页、频控退避和断点跳过用例验证长列表。
- 用真实 `python-docx` 写读验证标题、元数据和正文。
- 对 DOCX 内 `word/media` 与源图片逐字节比对，并验证大图等比适配版心。
- 用伪 `NoteSource` 验证批量导出和失败隔离。
- Playwright 浏览器启动只在 `doctor` 或人工集成测试中验证。

## Windows 交付

桌面版使用 PySide6。后台导出任务通过 QThread 和 Qt 信号更新界面，避免阻塞窗口；
发布版使用 PyInstaller 生成单目录应用，包含 Playwright、PySide6 和 Word 写库所需运行时，
并继续使用 Windows 自带的 Edge。安装包阶段使用 Inno Setup 或 MSIX。
