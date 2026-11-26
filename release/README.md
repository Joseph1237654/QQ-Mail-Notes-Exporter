# QQNoteExporter 0.1.4

本目录包含可分发安装包、便携版、自签名公钥证书和 SHA256 校验值。源代码位于仓库
根目录，本目录不包含任何用户笔记、导出 DOCX、浏览器配置或日志。

## 0.1.4 更新

- 程序默认名称、可执行文件、安装器和发布包统一更名为 `QQNoteExporter`。
- 将导出路径设置移入独立设置窗口，并在左下角提供齿轮入口。
- 新增“关于我们”页面，展示当前版本、软件名称和设计理念。
- 移除标题栏中的 `WINDOWS DESKTOP` 副标题，简化顶部信息。
- 应用图标改为透明着色线稿，使标题栏和设置页的背景更统一。
- 保留 0.1.3 的导出状态恢复、目录重选和接口限流降速修复。

## 文件

- `QQNoteExporter-Setup-0.1.4.exe`：Windows 安装程序。
- `QQNoteExporter-Portable-0.1.4.zip`：解压后双击
  `QQNoteExporter.exe` 运行。
- `QQNotebookExporter-LocalSigning.cer`：用于验证发布文件签名的自签名公钥证书。
- `SHA256SUMS.txt`：发布文件校验值。

## 签名说明

主程序和安装程序已使用 `CN=QQ Notebook Exporter Local Signing` 完成 Authenticode
签名并添加时间戳。该证书是本地自签名证书，不是 CA 颁发的受信任代码签名证书，因此
Windows SmartScreen 仍可能显示“未知发布者”。

在其他机器上，可以手动将 `QQNotebookExporter-LocalSigning.cer` 导入“受信任的发布者”
后验证签名。导入自签名证书会改变本机信任设置，应由使用者自行决定。

查看签名状态：

```powershell
Get-AuthenticodeSignature .\QQNoteExporter-Setup-0.1.4.exe |
    Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

校验 SHA256：

```powershell
Get-FileHash .\QQNoteExporter-Setup-0.1.4.exe -Algorithm SHA256
Get-FileHash .\QQNoteExporter-Portable-0.1.4.zip -Algorithm SHA256
```

## 隐私边界

发布内容只包含程序代码、运行时依赖和图标资源。构建与发布检查会拒绝
`exports/`、`browser-profile`、DOCX、PDF、日志、Cookie、SQLite 数据库和本机隐私路径
标记。
