import base64
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from docx import Document

from qq_notebook_exporter.docx_exporter import WORD_NS, DocxExporter
from qq_notebook_exporter.errors import ExportError
from qq_notebook_exporter.filenames import build_note_filename
from qq_notebook_exporter.models import Note


def test_export_note_preserves_title_and_body(tmp_path) -> None:
    note = Note(
        note_id="_3012",
        subject="项目周记",
        content=(
            "<p>第一段包含 <strong>重点</strong> 和 <a href='https://example.com'>链接</a>。</p>"
            "<h2>下一步</h2><ul><li>补充测试</li><li>提交 PR</li></ul>"
        ),
        category_name="工作",
        created_at=datetime(2026, 11, 20, 8, 0, tzinfo=UTC),
        updated_at=datetime(2026, 11, 21, 9, 30, tzinfo=UTC),
    )

    outcome = DocxExporter().export_note(note, tmp_path)

    assert outcome.created is True
    assert outcome.path.name == "项目周记__3012.docx"

    document = Document(outcome.path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    assert document.core_properties.title == "项目周记"
    assert paragraphs[0] == "项目周记"
    assert any("第一段包含" in text for text in paragraphs)
    assert "下一步" in paragraphs
    assert "补充测试" in paragraphs


def test_export_note_skips_existing_file_by_default(tmp_path) -> None:
    note = Note(note_id="_1", subject="标题", content="<p>正文</p>")
    exporter = DocxExporter()

    first = exporter.export_note(note, tmp_path)
    second = exporter.export_note(note, tmp_path)

    assert first.created is True
    assert second.created is False
    assert first.path == second.path


def test_inline_container_stays_in_one_paragraph(tmp_path) -> None:
    note = Note(
        note_id="_3",
        subject="内联格式",
        content="<div>前缀 <strong>重点</strong> 后缀</div>",
    )

    outcome = DocxExporter().export_note(note, tmp_path)
    document = Document(outcome.path)
    paragraph_texts = [paragraph.text for paragraph in document.paragraphs]

    assert "前缀 重点 后缀" in paragraph_texts


def test_export_uses_a4_and_heading_font(tmp_path) -> None:
    note = Note(note_id="_4", subject="页面", content="<h4>四级标题</h4><p>正文</p>")

    outcome = DocxExporter().export_note(note, tmp_path)
    document = Document(outcome.path)
    section = document.sections[0]

    assert round(section.page_width.mm) == 210
    assert round(section.page_height.mm) == 297
    assert document.styles["Heading 4"].font.name == "Microsoft YaHei"


def test_export_fixes_required_zoom_percent(tmp_path) -> None:
    note = Note(note_id="_5", subject="结构", content="<p>正文</p>")

    outcome = DocxExporter().export_note(note, tmp_path)

    with ZipFile(outcome.path) as package:
        settings = ElementTree.fromstring(package.read("word/settings.xml"))
    zoom = settings.find(f"{{{WORD_NS}}}zoom")
    assert zoom is not None
    assert zoom.get(f"{{{WORD_NS}}}percent") == "100"


def test_existing_corrupt_docx_is_replaced(tmp_path) -> None:
    note = Note(note_id="_6", subject="损坏文件", content="<p>正文</p>")
    target = tmp_path / build_note_filename(note.display_title, note.note_id)
    target.write_bytes(b"not a zip")

    outcome = DocxExporter().export_note(note, tmp_path)

    assert outcome.created is True
    with ZipFile(outcome.path) as package:
        assert "word/document.xml" in package.namelist()


def test_failed_save_leaves_no_partial_target(tmp_path, monkeypatch) -> None:
    note = Note(note_id="_7", subject="失败写入", content="<p>正文</p>")
    target = tmp_path / build_note_filename(note.display_title, note.note_id)

    class FailingDocument:
        def save(self, path) -> None:
            Path(path).write_bytes(b"partial")
            raise OSError("disk full")

    monkeypatch.setattr(
        DocxExporter,
        "_build_document",
        lambda _self, _note: FailingDocument(),
    )

    with pytest.raises(ExportError):
        DocxExporter().export_note(note, tmp_path)

    assert not target.exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_nested_lists_preserve_hierarchy(tmp_path) -> None:
    note = Note(
        note_id="_8",
        subject="嵌套列表",
        content="<ul><li>父项目<ul><li>子项目</li></ul></li><li>第二项</li></ul>",
    )

    outcome = DocxExporter().export_note(note, tmp_path)
    document = Document(outcome.path)
    items = {
        paragraph.text: _numbering_level(paragraph)
        for paragraph in document.paragraphs
        if paragraph.text in {"父项目", "子项目", "第二项"}
    }

    assert items == {"父项目": 0, "子项目": 1, "第二项": 0}


def test_separate_ordered_lists_use_independent_numbering(tmp_path) -> None:
    note = Note(
        note_id="_9",
        subject="独立编号",
        content="<ol><li>甲</li><li>乙</li></ol><p>中间</p><ol><li>丙</li><li>丁</li></ol>",
    )

    outcome = DocxExporter().export_note(note, tmp_path)
    document = Document(outcome.path)
    num_ids = {
        paragraph.text: _numbering_id(paragraph)
        for paragraph in document.paragraphs
        if paragraph.text in {"甲", "乙", "丙", "丁"}
    }

    assert num_ids["甲"] == num_ids["乙"]
    assert num_ids["丙"] == num_ids["丁"]
    assert num_ids["甲"] != num_ids["丙"]


def test_export_embeds_data_uri_image_without_recompression(tmp_path) -> None:
    image_bytes = _png_bytes(8, 6)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    note = Note(
        note_id="_10",
        subject="原始图片",
        content=(
            "<p>图片说明</p>"
            f'<p><img src="data:image/png;base64,{encoded}" alt="照片"></p>'
        ),
    )

    outcome = DocxExporter().export_note(note, tmp_path)

    with ZipFile(outcome.path) as package:
        media_names = [
            name for name in package.namelist() if name.startswith("word/media/")
        ]
        assert len(media_names) == 1
        assert package.read(media_names[0]) == image_bytes

    document = Document(outcome.path)
    assert len(document.inline_shapes) == 1
    assert "[图片]" not in "\n".join(paragraph.text for paragraph in document.paragraphs)


def test_export_fetches_remote_image_using_page_credentials(tmp_path) -> None:
    image_bytes = _png_bytes(12, 9)
    requested_urls: list[str] = []

    def fetch_image(url: str) -> bytes:
        requested_urls.append(url)
        return image_bytes

    note = Note(
        note_id="_11",
        subject="远程图片",
        content='<img data-src="//cdn.example.test/photo.png">',
    )

    outcome = DocxExporter(fetch_image).export_note(note, tmp_path)

    assert requested_urls == ["https://cdn.example.test/photo.png"]
    with ZipFile(outcome.path) as package:
        media = package.read(
            next(name for name in package.namelist() if name.startswith("word/media/"))
        )
    assert media == image_bytes


def test_export_normalizes_markdown_wrapped_image_url(tmp_path) -> None:
    image_bytes = _png_bytes(12, 9)
    photo_url = "https://cdn.example.test/photo.jpg?width=1200&height=900"
    requested_urls: list[str] = []

    def fetch_image(url: str) -> bytes:
        requested_urls.append(url)
        return image_bytes

    escaped_photo_url = photo_url.replace("&", "\\&")
    note = Note(
        note_id="_11a",
        subject="Markdown 图片地址",
        content=f'<img data-original="[{photo_url}]({escaped_photo_url})">',
    )

    outcome = DocxExporter(fetch_image).export_note(note, tmp_path)

    assert requested_urls == [photo_url]
    document = Document(outcome.path)
    assert len(document.inline_shapes) == 1


def test_export_falls_back_to_next_image_source(tmp_path) -> None:
    image_bytes = _png_bytes(12, 9)
    broken_url = "https://cdn.example.test/broken.jpg"
    photo_url = "https://cdn.example.test/photo.png"
    requested_urls: list[str] = []

    def fetch_image(url: str) -> bytes:
        requested_urls.append(url)
        if url == broken_url:
            return b"<html>not an image</html>"
        return image_bytes

    note = Note(
        note_id="_11b",
        subject="图片地址回退",
        content=f'<img data-original="{broken_url}" src="{photo_url}">',
    )

    outcome = DocxExporter(fetch_image).export_note(note, tmp_path)

    assert requested_urls == [broken_url, photo_url]
    document = Document(outcome.path)
    assert len(document.inline_shapes) == 1


def test_export_scales_large_image_to_page_without_changing_aspect_ratio(tmp_path) -> None:
    image_bytes = _png_bytes(4000, 1000)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    note = Note(
        note_id="_12",
        subject="大图适配",
        content=f'<img src="data:image/png;base64,{encoded}">',
    )

    outcome = DocxExporter().export_note(note, tmp_path)
    document = Document(outcome.path)
    shape = document.inline_shapes[0]

    assert shape.width.mm <= 162.1
    assert shape.width.mm / shape.height.mm == pytest.approx(4.0, rel=0.01)
    with ZipFile(outcome.path) as package:
        media_name = next(
            name for name in package.namelist() if name.startswith("word/media/")
        )
        assert package.read(media_name) == image_bytes


def test_missing_remote_image_fails_instead_of_silently_dropping_it(tmp_path) -> None:
    note = Note(
        note_id="_13",
        subject="图片缺失",
        content='<img src="https://cdn.example.test/private.png">',
    )
    target = tmp_path / build_note_filename(note.display_title, note.note_id)

    with pytest.raises(ExportError, match="缺少图片获取器"):
        DocxExporter().export_note(note, tmp_path)

    assert not target.exists()


def _png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    rows = b"".join(b"\x00" + b"\x24\x24\x24" * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _numbering(paragraph) -> tuple[str | None, str | None]:
    num_properties = paragraph._p.pPr.numPr
    num_id = num_properties.numId.val if num_properties.numId is not None else None
    level = num_properties.ilvl.val if num_properties.ilvl is not None else None
    return num_id, level


def _numbering_id(paragraph) -> str | None:
    return _numbering(paragraph)[0]


def _numbering_level(paragraph) -> int | None:
    level = _numbering(paragraph)[1]
    return int(level) if level is not None else None
