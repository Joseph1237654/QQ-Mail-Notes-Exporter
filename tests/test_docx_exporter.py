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
