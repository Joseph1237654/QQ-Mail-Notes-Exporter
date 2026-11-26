from __future__ import annotations

import re
from typing import Literal

Language = Literal["zh_CN", "en"]

DEFAULT_LANGUAGE: Language = "zh_CN"
SUPPORTED_LANGUAGES: tuple[tuple[Language, str], ...] = (
    ("zh_CN", "简体中文"),
    ("en", "English"),
)

_TRANSLATIONS: dict[Language, dict[str, str]] = {
    "zh_CN": {
        "app.brand": "QQ邮箱记事本导出器",
        "app.icon_accessible": "QQ邮箱记事本导出器图标",
        "header.logged_out": "未登录",
        "header.logged_in": "已登录",
        "header.completed": "已完成",
        "header.error": "出错",
        "header.waiting_login": "等待登录",
        "header.exporting": "正在导出",
        "sections.account": "账户",
        "sections.export": "导出",
        "sections.progress": "进度",
        "sections.activity": "活动",
        "account.not_signed_in": "尚未登录",
        "account.waiting_browser": "等待浏览器登录",
        "account.readable": "首屏可读取 {total} 条笔记",
        "account.task_failed": "任务失败",
        "buttons.login": "登录 QQ 邮箱",
        "buttons.start_export": "开始导出",
        "buttons.open_settings": "打开设置",
        "buttons.open_folder": "打开目录",
        "metrics.total": "总计",
        "metrics.exported": "已导出",
        "metrics.failed": "失败",
        "current.waiting_start": "等待开始",
        "current.complete_sign_in": "请在 Edge 中完成登录",
        "current.session_verified": "登录态已验证",
        "current.export_complete": "导出完成",
        "current.task_failed": "任务失败",
        "current.preparing": "准备读取记事本",
        "current.progress": "{index} / {total} · {status} · {title}",
        "activity.placeholder": "导出记录会显示在这里",
        "progress.processing": "处理中",
        "log.login_opening": "正在打开 QQ 邮箱登录窗口",
        "log.login_required": "请先完成 QQ 邮箱登录",
        "log.export_started": "开始导出到 {path}",
        "log.login_succeeded": "登录成功，首屏可读取 {total} 条笔记",
        "log.export_finished": (
            "导出完成：{exported} 条成功，{skipped} 条跳过，{failed} 条失败"
        ),
        "log.failure": "失败 [{note_id}] {title}: {message}",
        "log.progress_failure": "失败：{title}",
        "log.error": "错误：{message}",
        "log.language_changed": "已将界面语言切换为简体中文。",
        "error.create_output_dir": "无法创建导出目录：{error}",
        "dialog.task_running.title": "任务进行中",
        "dialog.task_running.body": "请等待当前任务结束后再关闭窗口。",
        "settings.window_title": "设置",
        "settings.title": "设置",
        "settings.nav.path": "导出路径",
        "settings.nav.language": "界面语言",
        "settings.nav.about": "关于我们",
        "settings.close": "关闭",
        "settings.close_tooltip": "关闭设置",
        "settings.path.description": "设置 Word 文档的保存位置。每条笔记会生成一个独立文件。",
        "settings.path.label": "保存位置",
        "settings.path.placeholder": "选择 Word 导出目录",
        "settings.path.accessible": "导出路径",
        "settings.choose_directory": "选择目录",
        "settings.choose_directory_tooltip": "选择 Word 文件的保存位置",
        "settings.language.description": "选择整个应用使用的界面语言。",
        "settings.language.label": "界面语言",
        "settings.language.hint": "保存设置后，整个界面会立即切换语言。",
        "settings.version": "版本 {version}",
        "settings.tagline": "让散落的个人记录被妥善保存。",
        "settings.philosophy_title": "设计理念",
        "settings.philosophy_body": (
            "把散落在 QQ 邮箱记事本里的个人记录，整理成可长期保存、便于检索和迁移的"
            " Word 文档。软件坚持本地优先，不接收或保存 QQ 密码，导出结果只写入用户"
            "指定的目录。界面保持克制，流程尽量直接，让每一次导出都清晰、可预期。"
        ),
        "buttons.cancel": "取消",
        "buttons.save": "保存",
        "settings.save_tooltip": "保存设置",
        "settings.path_required_title": "导出路径",
        "settings.path_required_message": "请先选择 Word 导出目录。",
        "settings.invalid_dir_message": "无法使用该目录：{error}",
        "filedialog.choose_word_dir": "选择 Word 导出目录",
        "status.exported": "已导出",
        "status.existing": "已存在",
        "status.failed": "失败",
    },
    "en": {
        "app.brand": "QQ Mail Notebook Exporter",
        "app.icon_accessible": "QQ Mail Notebook Exporter icon",
        "header.logged_out": "Not signed in",
        "header.logged_in": "Signed in",
        "header.completed": "Completed",
        "header.error": "Error",
        "header.waiting_login": "Signing in",
        "header.exporting": "Exporting",
        "sections.account": "Account",
        "sections.export": "Export",
        "sections.progress": "Progress",
        "sections.activity": "Activity",
        "account.not_signed_in": "Not signed in",
        "account.waiting_browser": "Waiting for browser sign-in",
        "account.readable": "{total} notes available on the first page",
        "account.task_failed": "Task failed",
        "buttons.login": "Sign in to QQ Mail",
        "buttons.start_export": "Start export",
        "buttons.open_settings": "Open settings",
        "buttons.open_folder": "Open folder",
        "metrics.total": "Total",
        "metrics.exported": "Exported",
        "metrics.failed": "Failed",
        "current.waiting_start": "Ready",
        "current.complete_sign_in": "Complete sign-in in Edge",
        "current.session_verified": "Session verified",
        "current.export_complete": "Export complete",
        "current.task_failed": "Task failed",
        "current.preparing": "Preparing notes",
        "current.progress": "{index} / {total} · {status} · {title}",
        "activity.placeholder": "Export activity will appear here",
        "progress.processing": "Processing",
        "log.login_opening": "Opening the QQ Mail sign-in window",
        "log.login_required": "Sign in to QQ Mail first",
        "log.export_started": "Exporting to {path}",
        "log.login_succeeded": "Signed in; {total} notes available on the first page",
        "log.export_finished": (
            "Export complete: {exported} exported, {skipped} skipped, {failed} failed"
        ),
        "log.failure": "Failed [{note_id}] {title}: {message}",
        "log.progress_failure": "Failed: {title}",
        "log.error": "Error: {message}",
        "log.language_changed": "Interface language changed to English.",
        "error.create_output_dir": "Could not create the export folder: {error}",
        "dialog.task_running.title": "Task in progress",
        "dialog.task_running.body": "Wait for the current task to finish before closing.",
        "settings.window_title": "Settings",
        "settings.title": "Settings",
        "settings.nav.path": "Export path",
        "settings.nav.language": "Language",
        "settings.nav.about": "About",
        "settings.close": "Close",
        "settings.close_tooltip": "Close settings",
        "settings.path.description": (
            "Set where Word documents are saved. Each note is saved as a separate file."
        ),
        "settings.path.label": "Save location",
        "settings.path.placeholder": "Choose a Word export folder",
        "settings.path.accessible": "Export path",
        "settings.choose_directory": "Choose folder",
        "settings.choose_directory_tooltip": "Choose where Word files are saved",
        "settings.language.description": "Choose the language used throughout the app.",
        "settings.language.label": "Interface language",
        "settings.language.hint": "The entire interface switches immediately after saving.",
        "settings.version": "Version {version}",
        "settings.tagline": "Keep scattered personal notes safely preserved.",
        "settings.philosophy_title": "Design principles",
        "settings.philosophy_body": (
            "Turn personal notes scattered across QQ Mail Notebook into Word documents "
            "that are easy to keep, search, and migrate. The app is local-first: it never "
            "receives or stores your QQ password, and exports are written only to the "
            "folder you choose. The interface stays restrained and the workflow stays "
            "direct, so every export is clear and predictable."
        ),
        "buttons.cancel": "Cancel",
        "buttons.save": "Save",
        "settings.save_tooltip": "Save settings",
        "settings.path_required_title": "Export path",
        "settings.path_required_message": "Choose a Word export folder first.",
        "settings.invalid_dir_message": "This folder cannot be used: {error}",
        "filedialog.choose_word_dir": "Choose a Word export folder",
        "status.exported": "Exported",
        "status.existing": "Already exists",
        "status.failed": "Failed",
    },
}

_EN_ERROR_EXACT = {
    "未检测到可用的 QQ 邮箱登录态。请完成登录并进入记事本页面。": (
        "No active QQ Mail session was found. Sign in and open Notebook."
    ),
    "未安装 Playwright。请执行: python -m pip install -e .": (
        "Playwright is not installed. Run: python -m pip install -e ."
    ),
    "无法启动浏览器。请确认 Microsoft Edge 已安装，或尝试参数 --channel chromium。": (
        "Could not start the browser. Make sure Microsoft Edge is installed, "
        "or try --channel chromium."
    ),
    "浏览器页面尚未初始化。": "The browser page is not ready.",
    "未检测到 QQ 邮箱登录态。请重新执行 login，并完成登录和记事本页面加载。": (
        "No QQ Mail session was found. Sign in again and wait for Notebook to load."
    ),
    "QQ 记事本接口请求失败，可稍后重试。": (
        "The QQ Notebook request failed. Try again later."
    ),
    "页面内请求没有返回有效结果。": "The page request did not return a valid result.",
    "QQ 记事本接口返回了非 JSON 内容，登录态可能已失效。": (
        "The QQ Notebook API returned non-JSON content. The session may have expired."
    ),
    "QQ 记事本接口返回格式异常。": "The QQ Notebook API returned an unexpected format.",
    "QQ 邮箱 sid 为空。": "The QQ Mail session ID is empty.",
    "QQ 记事本接口缺少 head 字段。": "The QQ Notebook API response is missing the head field.",
    "QQ 记事本接口缺少 body 字段。": "The QQ Notebook API response is missing the body field.",
    "登录态已失效。": "The sign-in session has expired.",
    "操作过于频繁，请稍后再试。": "Too many requests. Try again later.",
    "未知错误": "Unknown error",
    "笔记包含空图片地址，无法完整导出。": (
        "A note contains an image with an empty address and cannot be exported completely."
    ),
    "笔记包含没有地址的图片，无法完整导出。": (
        "A note contains an image without an address and cannot be exported completely."
    ),
    "笔记包含没有可用地址的图片，无法完整导出。": (
        "A note contains an image without a usable address and cannot be exported completely."
    ),
    "图片 data URI 格式无效。": "The image data URI is invalid.",
    "图片 data URI 解码失败。": "The image data URI could not be decoded.",
}

_EN_ERROR_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"^笔记 (.+) 的完整正文缺失，拒绝使用摘要导出。$",
        r"The full body for note \1 is missing; the summary was not used.",
    ),
    (r"^无法打开页面: (.+)$", r"Could not open the page: \1"),
    (r"^图片请求失败: HTTP (\d+) (.+)$", r"Image request failed: HTTP \1 \2"),
    (r"^图片请求失败: (.+)$", r"Image request failed: \1"),
    (r"^图片响应为空: (.+)$", r"The image response was empty: \1"),
    (r"^QQ 记事本接口暂时不可用: HTTP (\d+)$", r"QQ Notebook is temporarily unavailable: HTTP \1"),
    (r"^QQ 记事本接口 HTTP 状态异常: (\d+)$", r"QQ Notebook returned HTTP status \1"),
    (r"^QQ 记事本接口字段 (.+) 格式异常。$", r"QQ Notebook field \1 has an unexpected format."),
    (r"^写入 Word 文件失败: (.+)$", r"Could not write the Word document: \1"),
    (r"^图片格式不受 Word 支持: (.+)$", r"Word does not support this image format: \1"),
    (r"^不支持的图片地址: (.+)$", r"Unsupported image address: \1"),
    (r"^缺少图片获取器，无法下载: (.+)$", r"No image loader is available for: \1"),
    (r"^图片获取失败: (.+)$", r"Could not retrieve the image: \1"),
    (r"^图片内容为空: (.+)$", r"The image content was empty: \1"),
    (r"^生成的文件不是有效的 DOCX: (.+)$", r"The generated file is not a valid DOCX: \1"),
)


def normalize_language(value: object) -> Language:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"en", "en_us", "en_gb", "english"}:
        return "en"
    return DEFAULT_LANGUAGE


def translate(language: object, key: str, **values: object) -> str:
    normalized = normalize_language(language)
    template = _TRANSLATIONS.get(normalized, {}).get(key)
    if template is None:
        template = _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**values)


def translate_runtime_message(language: object, message: str) -> str:
    if normalize_language(language) != "en":
        return message

    translated = _EN_ERROR_EXACT.get(message)
    if translated is not None:
        return translated

    for pattern, replacement in _EN_ERROR_PATTERNS:
        if re.match(pattern, message):
            translated = re.sub(pattern, replacement, message)
            break
    else:
        translated = message

    if re.search(r"[\u4e00-\u9fff]", translated):
        return "The task failed. Please try again."
    return translated
