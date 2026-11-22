# Windows 打包

## 构建范围

发布包只包含程序代码、Python 运行时、PySide6、Playwright、python-docx 和
`qq_notebook_exporter/resources` 中的图标资源。构建过程不会复制仓库根目录，因此
`exports/`、浏览器配置、日志、测试文件、文档和 Git 元数据不会进入发布目录。

以下路径始终排除：

- `exports/`
- `%LOCALAPPDATA%\QQNotebookExporter\browser-profile`
- `tests/`、`docs/`、`.git/`、`.venv/`
- `.docx`、`.pdf`、`.log`、Cookie、History、SQLite 数据库等本地数据

`packaging/verify_release.py` 会在构建后再次检查发布目录，并扫描本机用户目录和已知
导出目录标记。任何命中都会让构建失败。

## 安装构建依赖

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[build,gui]"
```

## 构建便携目录

```powershell
python scripts\build_windows.py
```

输出：

```text
dist\QQNotebookExporter\
  QQNotebookExporter.exe
  _internal\
```

`dist/`、`build/` 和 `release/` 均已加入 `.gitignore`，不会被提交到 Git。

## 构建安装包

安装 Inno Setup 6 后执行：

```powershell
python scripts\build_windows.py --installer
```

也可以设置 `INNO_SETUP_COMPILER` 指向 `ISCC.exe`。安装包输出到 `release/`。

## 发布前检查

1. 确认 `git status --short` 中没有 DOCX、PDF、日志或浏览器配置。
2. 运行 `packaging/verify_release.py` 检查发布目录。
3. 在未安装 Python 的 Windows 11 机器上安装并启动程序。
4. 手动完成 QQ 邮箱登录、单条导出和图片完整性检查。
5. 不把 `exports/`、`dist/`、`release/` 或浏览器配置作为源码提交。
