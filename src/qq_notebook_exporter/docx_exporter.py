from __future__ import annotations

import base64
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes, urljoin, urlparse
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.document import Document as DocumentType
from docx.image.image import Image as DocxImage
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

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
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MARKUP_COMPATIBILITY_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
ImageFetcher = Callable[[str], bytes]
ImageLoader = Callable[[str], bytes]


@dataclass(frozen=True, slots=True)
class ExportOutcome:
    path: Path
    created: bool


class DocxExporter:
    def __init__(
        self,
        image_fetcher: ImageFetcher | None = None,
        *,
        image_base_url: str = "https://wx.mail.qq.com/",
    ) -> None:
        self._image_fetcher = image_fetcher
        self._image_base_url = image_base_url

    @staticmethod
    def expected_path(output_dir: Path, title: str, note_id: str) -> Path:
        return output_dir / build_note_filename(title, note_id)

    def has_valid_output(self, output_dir: Path, title: str, note_id: str) -> bool:
        path = self.expected_path(output_dir, title, note_id)
        return path.exists() and _validate_docx_package(path)

    def export_note(
        self,
        note: Note,
        output_dir: Path,
        *,
        overwrite: bool = False,
    ) -> ExportOutcome:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = self.expected_path(output_dir, note.display_title, note.note_id)

        if path.exists() and not overwrite and _validate_docx_package(path):
            return ExportOutcome(path=path, created=False)

        temp_path = output_dir / f".{path.stem}.{uuid4().hex}.tmp"
        try:
            document = self._build_document(note)
            document.save(temp_path)
            _normalize_docx_package(temp_path)
            _validate_docx_package(temp_path, raise_on_error=True)
            os.replace(temp_path, path)
        except ExportError:
            temp_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            raise ExportError(f"写入 Word 文件失败: {path}") from exc

        return ExportOutcome(path=path, created=True)

    def _build_document(self, note: Note) -> DocumentType:
        document = Document()
        self._configure_page(document)
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

        image_cache: dict[str, bytes] = {}

        def load_image(source: str) -> bytes:
            cached = image_cache.get(source)
            if cached is not None:
                return cached
            blob = self._resolve_image(source)
            try:
                DocxImage.from_blob(blob)
            except Exception as exc:
                raise ExportError(f"图片格式不受 Word 支持: {source}") from exc
            image_cache[source] = blob
            return blob

        _add_content(document, note.content, load_image)
        return document

    def _resolve_image(self, source: str) -> bytes:
        cleaned = source.strip()
        if not cleaned:
            raise ExportError("笔记包含空图片地址，无法完整导出。")

        if cleaned.lower().startswith("data:"):
            return _decode_data_uri(cleaned)

        absolute_url = urljoin(self._image_base_url, cleaned)
        if urlparse(absolute_url).scheme.lower() not in {"http", "https"}:
            raise ExportError(f"不支持的图片地址: {source}")
        if self._image_fetcher is None:
            raise ExportError(f"缺少图片获取器，无法下载: {absolute_url}")

        try:
            blob = self._image_fetcher(absolute_url)
        except ExportError:
            raise
        except Exception as exc:
            raise ExportError(f"图片获取失败: {absolute_url}") from exc
        if not blob:
            raise ExportError(f"图片内容为空: {absolute_url}")
        return blob

    @staticmethod
    def _configure_page(document: DocumentType) -> None:
        section = document.sections[0]
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(22)
        section.bottom_margin = Mm(22)
        section.left_margin = Mm(24)
        section.right_margin = Mm(24)

    @staticmethod
    def _configure_styles(document: DocumentType) -> None:
        normal = document.styles["Normal"]
        normal.font.name = "Microsoft YaHei"
        normal.font.size = Pt(10.5)
        normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.2

        for style_name in (
            "Title",
            "Heading 1",
            "Heading 2",
            "Heading 3",
            "Heading 4",
            "Heading 5",
            "Heading 6",
        ):
            style = document.styles[style_name]
            style.font.name = "Microsoft YaHei"
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    @staticmethod
    def _format_datetime(value: Any) -> str:
        if value is None:
            return "未知"
        return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _add_content(
    document: DocumentType,
    content: str,
    image_loader: ImageLoader,
) -> None:
    if not content.strip():
        return

    soup = BeautifulSoup(content, "html.parser")
    container = soup.body or soup
    if not any(True for _ in container.find_all(True)):
        _add_plain_text(document, container.get_text())
        return

    _walk_blocks(document, container, image_loader)


def _walk_blocks(
    document: DocumentType,
    parent: Tag,
    image_loader: ImageLoader,
) -> None:
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
            _append_inline(paragraph, child, image_loader=image_loader)
            continue
        if name in {"ul", "ol"}:
            _walk_list(document, child, image_loader)
            continue
        if name == "blockquote":
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Pt(18)
            _append_inline(paragraph, child, image_loader=image_loader, italic=True)
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
            _walk_blocks(document, child, image_loader)
            continue

        paragraph = document.add_paragraph()
        _append_inline(paragraph, child, image_loader=image_loader)


def _append_inline(
    paragraph: Any,
    node: Any,
    *,
    image_loader: ImageLoader,
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
        source = _image_source(node)
        if not source:
            raise ExportError("笔记包含没有地址的图片，无法完整导出。")
        blob = image_loader(source)
        _add_inline_picture(paragraph, blob)
        return

    next_bold = bold or name in {"b", "strong"}
    next_italic = italic or name in {"i", "em"}
    next_code = code or name == "code"
    next_underline = underline or name == "a"

    for child in node.children:
        _append_inline(
            paragraph,
            child,
            image_loader=image_loader,
            bold=next_bold,
            italic=next_italic,
            code=next_code,
            underline=next_underline,
        )

    if name == "a":
        href = str(node.get("href") or "").strip()
        if href and not href.startswith("#"):
            paragraph.add_run(f" ({href})")


def _walk_list(
    document: DocumentType,
    list_tag: Tag,
    image_loader: ImageLoader,
    level: int = 0,
) -> None:
    ordered = list_tag.name.lower() == "ol"
    numbering_id = _create_list_numbering(document, ordered=ordered)
    for item in list_tag.find_all("li", recursive=False):
        paragraph = document.add_paragraph()
        _apply_numbering(paragraph, numbering_id, level)
        for child in item.children:
            if isinstance(child, Tag) and child.name.lower() in {"ul", "ol"}:
                continue
            _append_inline(paragraph, child, image_loader=image_loader)

        for nested in item.find_all(["ul", "ol"], recursive=False):
            _walk_list(document, nested, image_loader, level + 1)


def _image_source(node: Tag) -> str:
    for attribute in ("data-original", "data-src", "data-lazy-src", "src"):
        value = node.get(attribute)
        if value is None:
            continue
        source = str(value).strip()
        if source:
            return source
    return ""


def _add_inline_picture(paragraph: Any, blob: bytes) -> None:
    image = DocxImage.from_blob(blob)
    section = paragraph.part.document.sections[-1]
    max_width = int(section.page_width - section.left_margin - section.right_margin)
    max_height = int(section.page_height - section.top_margin - section.bottom_margin)
    natural_width = int(image.width)
    natural_height = int(image.height)

    width = natural_width
    height = natural_height
    if natural_width > 0 and natural_height > 0:
        scale = min(
            1.0,
            max_width / natural_width,
            max_height / natural_height,
        )
        width = max(1, int(natural_width * scale))
        height = max(1, int(natural_height * scale))

    paragraph.add_run().add_picture(
        BytesIO(blob),
        width=width or None,
        height=height or None,
    )


def _create_list_numbering(document: DocumentType, *, ordered: bool) -> int:
    numbering = document.part.numbering_part.element
    abstract_ids = [
        int(element.get(qn("w:abstractNumId")))
        for element in numbering.findall(qn("w:abstractNum"))
        if element.get(qn("w:abstractNumId"))
    ]
    num_ids = [
        int(element.get(qn("w:numId")))
        for element in numbering.findall(qn("w:num"))
        if element.get(qn("w:numId"))
    ]
    abstract_id = max(abstract_ids, default=-1) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi_level = OxmlElement("w:multiLevelType")
    multi_level.set(qn("w:val"), "hybridMultilevel")
    abstract.append(multi_level)

    for level in range(9):
        abstract.append(_list_level_element(level, ordered=ordered))

    existing_nums = numbering.findall(qn("w:num"))
    if existing_nums:
        numbering.insert(numbering.index(existing_nums[0]), abstract)
    else:
        numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)
    return num_id


def _list_level_element(level: int, *, ordered: bool) -> Any:
    level_element = OxmlElement("w:lvl")
    level_element.set(qn("w:ilvl"), str(level))

    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    level_element.append(start)

    number_format = OxmlElement("w:numFmt")
    number_format.set(qn("w:val"), "decimal" if ordered else "bullet")
    level_element.append(number_format)

    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), f"%{level + 1}." if ordered else "•")
    level_element.append(level_text)

    justification = OxmlElement("w:lvlJc")
    justification.set(qn("w:val"), "left")
    level_element.append(justification)

    paragraph_properties = OxmlElement("w:pPr")
    indentation = OxmlElement("w:ind")
    indentation.set(qn("w:left"), str((level + 1) * 720))
    indentation.set(qn("w:hanging"), "360")
    paragraph_properties.append(indentation)
    level_element.append(paragraph_properties)

    if not ordered:
        run_properties = OxmlElement("w:rPr")
        fonts = OxmlElement("w:rFonts")
        fonts.set(qn("w:ascii"), "Segoe UI Symbol")
        fonts.set(qn("w:hAnsi"), "Segoe UI Symbol")
        run_properties.append(fonts)
        level_element.append(run_properties)

    return level_element


def _apply_numbering(paragraph: Any, num_id: int, level: int) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    num_properties = OxmlElement("w:numPr")

    level_element = OxmlElement("w:ilvl")
    level_element.set(qn("w:val"), str(level))
    num_properties.append(level_element)

    num_element = OxmlElement("w:numId")
    num_element.set(qn("w:val"), str(num_id))
    num_properties.append(num_element)
    paragraph_properties.append(num_properties)


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


def _decode_data_uri(value: str) -> bytes:
    header, separator, payload = value.partition(",")
    if not separator:
        raise ExportError("图片 data URI 格式无效。")
    try:
        if ";base64" in header.lower():
            return base64.b64decode(payload, validate=True)
        return unquote_to_bytes(payload)
    except (ValueError, TypeError) as exc:
        raise ExportError("图片 data URI 解码失败。") from exc


def _normalize_docx_package(path: Path) -> None:
    with ZipFile(path, "r") as package:
        entries = [(entry, package.read(entry.filename)) for entry in package.infolist()]

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as package:
        for entry, data in entries:
            if entry.filename == "word/settings.xml":
                data = _normalize_settings_xml(data)
            package.writestr(entry, data)


def _normalize_settings_xml(data: bytes) -> bytes:
    ElementTree.register_namespace("w", WORD_NS)
    root = ElementTree.fromstring(data)
    root.attrib.pop(f"{{{MARKUP_COMPATIBILITY_NS}}}Ignorable", None)
    zoom = root.find(f"{{{WORD_NS}}}zoom")
    if zoom is None:
        zoom = ElementTree.Element(f"{{{WORD_NS}}}zoom")
        root.insert(0, zoom)
    zoom.set(f"{{{WORD_NS}}}percent", "100")
    if zoom.get(f"{{{WORD_NS}}}val") is None:
        zoom.set(f"{{{WORD_NS}}}val", "bestFit")
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _validate_docx_package(path: Path, *, raise_on_error: bool = False) -> bool:
    required_members = {"[Content_Types].xml", "word/document.xml", "word/settings.xml"}
    try:
        with ZipFile(path, "r") as package:
            names = set(package.namelist())
            if not required_members.issubset(names):
                raise ValueError("DOCX package is missing required members")
            if package.testzip() is not None:
                raise ValueError("DOCX ZIP member checksum failed")

            settings = ElementTree.fromstring(package.read("word/settings.xml"))
            zoom = settings.find(f"{{{WORD_NS}}}zoom")
            if zoom is None or not zoom.get(f"{{{WORD_NS}}}percent"):
                raise ValueError("DOCX settings.xml has invalid w:zoom")

            ElementTree.fromstring(package.read("word/document.xml"))
            ElementTree.fromstring(package.read("[Content_Types].xml"))
    except (BadZipFile, KeyError, OSError, ValueError, ElementTree.ParseError) as exc:
        if raise_on_error:
            raise ValueError(f"生成的文件不是有效的 DOCX: {path}") from exc
        return False
    return True
