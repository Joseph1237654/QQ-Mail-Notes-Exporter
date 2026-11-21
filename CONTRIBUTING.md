# 贡献与版本管理

本项目按小步 PR 维护。每次 PR 只解决一个清晰问题，避免把登录、接口、Word
渲染和打包改动混在一起。

## 分支命名

- `feat/short-description`
- `fix/short-description`
- `test/short-description`
- `docs/short-description`

## PR 要求

1. 从最新 `main` 创建分支。
2. 修改范围与 PR 标题一致。
3. 新增行为必须有离线测试，不把真实邮箱凭据、Cookie 或导出内容提交到仓库。
4. 本地执行 `ruff check .` 和 `pytest`。
5. PR 描述中写明变更、验证方式和已知限制。

## 提交建议

使用 Conventional Commits：

```text
feat: add persistent QQ Mail login session
fix: handle empty notebook titles
test: cover docx title preservation
docs: define export resume format
```

## 敏感数据

禁止提交以下内容：

- QQ 账号密码、验证码、Cookie、`sid`
- `%LOCALAPPDATA%\QQNotebookExporter` 下的浏览器配置
- 真实记事本导出文件
- 浏览器调试日志中可能包含的登录信息
