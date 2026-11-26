# QQNoteExporter 0.1.5

本目录包含可分发安装包、便携版、自签名公钥证书和 SHA256 校验值。源代码位于仓库
根目录，本目录不包含任何用户笔记、导出 DOCX、浏览器配置或日志。

## 0.1.5 更新

- 设置窗口新增“界面语言”，支持简体中文和 English。
- 语言设置会持久保存，保存后主窗口、设置窗口、提示框和活动日志立即同步切换。
- 简体中文标题显示为“QQ邮箱记事本导出器”，英文标题显示为
  “QQ Mail Notebook Exporter”。
- 主界面按钮、状态、指标、设置页和关于页均提供完整中英文对应文案。
- 常见登录、接口、图片和 Word 写入错误也会跟随界面语言显示。
- 保留 0.1.4 的自定义安装目录、独立设置窗口、关于页和品牌图标更新。

## 文件

- `QQNoteExporter-Setup-0.1.5.exe`：Windows 安装程序。
- `QQNoteExporter-Portable-0.1.5.zip`：解压后双击
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
Get-AuthenticodeSignature .\QQNoteExporter-Setup-0.1.5.exe |
    Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

校验 SHA256：

```powershell
Get-FileHash .\QQNoteExporter-Setup-0.1.5.exe -Algorithm SHA256
Get-FileHash .\QQNoteExporter-Portable-0.1.5.zip -Algorithm SHA256
```

## 隐私边界

发布内容只包含程序代码、运行时依赖和图标资源。构建与发布检查会拒绝
`exports/`、`browser-profile`、DOCX、PDF、日志、Cookie、SQLite 数据库和本机隐私路径
标记。
