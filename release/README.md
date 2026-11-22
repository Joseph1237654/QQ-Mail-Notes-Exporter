# QQ 记事本导出 0.1.3

本目录包含可分发安装包、便携版、自签名公钥证书和 SHA256 校验值。源代码位于仓库
根目录，本目录不包含任何用户笔记、导出 DOCX、浏览器配置或日志。

## 0.1.3 更新

- 修复登录或导出结束后“导出目录”和目录选择按钮可能一直处于禁用状态的问题。
- 将目录按钮明确标记为“选择目录”，导出前目录为空时会再次打开选择窗口。
- 默认接口间隔从 1.25 秒恢复为 0.35 秒；遇到限流时自动逐级降速到 2 秒。
- 保留 0.1.2 的异常 JPEG EXIF 兼容和图片地址回退。

## 文件

- `QQNotebookExporter-Setup-0.1.3.exe`：Windows 安装程序。
- `QQNotebookExporter-Portable-0.1.3.zip`：解压后双击
  `QQNotebookExporter.exe` 运行。
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
Get-AuthenticodeSignature .\QQNotebookExporter-Setup-0.1.3.exe |
    Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

校验 SHA256：

```powershell
Get-FileHash .\QQNotebookExporter-Setup-0.1.3.exe -Algorithm SHA256
Get-FileHash .\QQNotebookExporter-Portable-0.1.3.zip -Algorithm SHA256
```

## 隐私边界

发布内容只包含程序代码、运行时依赖和图标资源。构建与发布检查会拒绝
`exports/`、`browser-profile`、DOCX、PDF、日志、Cookie、SQLite 数据库和本机隐私路径
标记。
