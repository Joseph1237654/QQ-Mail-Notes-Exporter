from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.ns import qn
from docx.shared import Pt

from qq_notebook_exporter.errors import ExportError
from qq_notebook_exporter.filenames import build_note_filename
from qq_notebook_exporter.models import Note

HEADING_TAGS = {
    "h1": 1,
    "h2": 2,
    "h3": 3,
    "h4": 4,
    "h5": 5,
    "h6": 6,
}
CONTAINER_TAGS = {"body", "html", "main", "article", "section", "div", "header", "footer"}
BLOCK_TAGS = CONTAINER_TAGS | set(HEADING_TAGS) | {
    "p",
    "ul",
    "ol",
    "blockquote",
    "pre",
    "table",
    "hr",
}
SKIPPED_TAGS = {"script", "style", "meta", "link"}


@dataclass(frozen=True, slots=True)
class ExportOutcome:
    path: Path
    created: bool


class DocxExporter:
    def export_note(
        self,
        note: Note,
        output_dir: Path,
        *,
        overwrite: bool = False,
    ) -> ExportOutcome:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / build_note_filename(note.display_title, note.note_id)

        if path.exists() and not overwrite:
            return ExportOutcome(path=path, created=False)

        try:
            document = self._build_document(note)
            document.save(path)
        except Exception as exc:
            raise ExportError(f"写入 Word 文件失败: {path}") from exc

        return ExportOutcome(path=path, created=True)

    def _build_document(self, note: Note) -> DocumentType:
        document = Document()
        self._configure_styles(document)

        title = note.display_title
        document.core_properties.title = title
        document.add_heading(title, level=1)

        metadata = document.add_paragraph()
        metadata.add_run("分类：").bold = True
        metadata.add_run(note.category_name or "未分类")
        metadata.add_run("    创建：").bold = True
        metadata.add_run(self._format_datetime(note.created_at))
        metadata.add_run("    修改：").bold = True
        metadata.add_run(self._format_datetime(note.updated_at))

        _add_content(document, note.content)
        return document

    @staticmethod
    def _configure_styles(document: DocumentType) -> None:
        normal = document.styles["Normal"]
        normal.font.name = "Microsoft YaHei"
        normal.font.size = Pt(10.5)
        normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

        for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
            style = document.styles[style_name]
            style.font.name = "Microsoft YaHei"
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    @staticmethod
    def _format_datetime(value: Any) -> str:
        if value is None:
            return "未知"
        return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _add_content(document: DocumentType, content: str) -> None:
    if not content.strip():
        return

    soup = BeautifulSoup(content, "html.parser")
    container = soup.body or soup
    if not any(True for _ in container.find_all(True)):
        _add_plain_text(document, container.get_text())
        return

    _walk_blocks(document, container)


def _walk_blocks(document: DocumentType, parent: Tag) -> None:
    for child in parent.children:
        if isinstance(child, NavigableString):
            text = _normalized_text(str(child))
            if text:
                document.add_paragraph(text)
            continue
        if not isinstance(child, Tag):
            continue

        name = child.name.lower()
        if name in SKIPPED_TAGS:
            continue
        if name in HEADING_TAGS:
            text = child.get_text(" ", strip=True)
            if text:
                document.add_heading(text, level=HEADING_TAGS[name])
            continue
        if name == "p":
            paragraph = document.add_paragraph()
            _append_inline(paragraph, child)
            continue
        if name in {"ul", "ol"}:
            style = "List Bullet" if name == "ul" else "List Number"
            for item in child.find_all("li", recursive=False):
                paragraph = document.add_paragraph(style=style)
                _append_inline(paragraph, item)
            continue
        if name == "blockquote":
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Pt(18)
            _append_inline(paragraph, child, italic=True)
            continue
        if name == "pre":
            paragraph = document.add_paragraph()
            run = paragraph.add_run(child.get_text())
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            continue
        if name == "br":
            document.add_paragraph()
            continue
        if name == "table":
            for row in child.find_all("tr"):
                cells = [
                    " ".join(cell.stripped_strings)
                    for cell in row.find_all(["th", "td"], recursive=False)
                ]
                if any(cells):
                    document.add_paragraph(" | ".join(cells))
            continue
        has_block_child = child.find(
            lambda tag: isinstance(tag, Tag) and tag.name.lower() in BLOCK_TAGS
        )
        if name in CONTAINER_TAGS and has_block_child:
            _walk_blocks(document, child)
            continue

        paragraph = document.add_paragraph()
        _append_inline(paragraph, child)


def _append_inline(
    paragraph: Any,
    node: Any,
    *,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
    underline: bool = False,
) -> None:
    if isinstance(node, NavigableString):
        text = re.sub(r"\s+", " ", str(node))
        if not text:
            return
        run = paragraph.add_run(text)
        run.bold = bold or None
        run.italic = italic or None
        run.underline = underline or None
        if code:
            run.font.name = "Consolas"
        return

    if not isinstance(node, Tag):
        return

    name = node.name.lower()
    if name == "br":
        paragraph.add_run().add_break()
        return
    if name == "img":
        paragraph.add_run("[图片]")
        return

    next_bold = bold or name in {"b", "strong"}
    next_italic = italic or name in {"i", "em"}
    next_code = code or name == "code"
    next_underline = underline or name == "a"

    for child in node.children:
        _append_inline(
            paragraph,
            child,
            bold=next_bold,
            italic=next_italic,
            code=next_code,
            underline=next_underline,
        )

    if name == "a":
        href = str(node.get("href") or "").strip()
        if href and not href.startswith("#"):
            paragraph.add_run(f" ({href})")


def _add_plain_text(document: DocumentType, content: str) -> None:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in normalized.split("\n\n") if block.strip()]
    for block in blocks:
        paragraph = document.add_paragraph()
        lines = block.split("\n")
        for index, line in enumerate(lines):
            paragraph.add_run(line)
            if index < len(lines) - 1:
                paragraph.add_run().add_break()


def _normalized_text(value: str) -> str:
    return " ".join(value.split())
