from datetime import UTC

import pytest

from qq_notebook_exporter.models import NoteSummary


def test_note_summary_preserves_title_and_metadata() -> None:
    summary = NoteSummary.from_api(
        {
            "noteid": "_3099",
            "subject": "  项目周记  ",
            "digest": "本周进展",
            "cataid": "2",
            "cata_name": "工作",
            "is_star": "1",
            "ctime": "1747653000",
            "utime": 1747739400,
            "size": "1234",
        }
    )

    assert summary.note_id == "_3099"
    assert summary.display_title == "项目周记"
    assert summary.category_id == 2
    assert summary.category_name == "工作"
    assert summary.is_starred is True
    assert summary.created_at is not None
    assert summary.created_at.tzinfo == UTC


def test_empty_title_uses_fallback() -> None:
    summary = NoteSummary(note_id="_1", subject="   ")
    assert summary.display_title == "无标题"


def test_note_id_is_required() -> None:
    with pytest.raises(ValueError, match="noteid"):
        NoteSummary.from_api({"subject": "无 ID"})
