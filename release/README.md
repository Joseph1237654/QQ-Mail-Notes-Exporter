# QQ 记事本导出 0.1.2

本目录包含可分发安装包、便携版、自签名公钥证书和 SHA256 校验值。源代码位于仓库
根目录，本目录不包含任何用户笔记、导出 DOCX、浏览器配置或日志。

## 0.1.2 更新

- 修复异常 JPEG EXIF 导致 Python-DOCX 拒绝图片的问题。
- 仅在解析失败时移除 JPEG APP1 元数据并补标准 JFIF 头，不重新编码像素数据。
- 保留 0.1.1 的 Markdown 图片地址规范化和备用地址回退。

## 文件

- `QQNotebookExporter-Setup-0.1.2.exe`：Windows 安装程序。
- `QQNotebookExporter-Portable-0.1.2.zip`：解压后双击
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
Get-AuthenticodeSignature .\QQNotebookExporter-Setup-0.1.2.exe |
    Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

校验 SHA256：

```powershell
Get-FileHash .\QQNotebookExporter-Setup-0.1.2.exe -Algorithm SHA256
Get-FileHash .\QQNotebookExporter-Portable-0.1.2.zip -Algorithm SHA256
```

## 隐私边界

发布内容只包含程序代码、运行时依赖和图标资源。构建与发布检查会拒绝
`exports/`、`browser-profile`、DOCX、PDF、日志、Cookie、SQLite 数据库和本机隐私路径
标记。
