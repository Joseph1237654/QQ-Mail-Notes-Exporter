from datetime import UTC, datetime

from docx import Document

from qq_notebook_exporter.docx_exporter import DocxExporter
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
