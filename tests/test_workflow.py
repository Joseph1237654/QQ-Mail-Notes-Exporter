from qq_notebook_exporter.docx_exporter import DocxExporter
from qq_notebook_exporter.models import Note, NoteSummary
from qq_notebook_exporter.workflow import ExportService


class FakeSource:
    def __init__(self, notes: list[Note], failing_ids: set[str] | None = None) -> None:
        self.notes = notes
        self.failing_ids = failing_ids or set()

    def list_notes(self) -> list[NoteSummary]:
        return [
            NoteSummary(note_id=note.note_id, subject=note.subject)
            for note in self.notes
        ]

    def read_note(self, summary: NoteSummary) -> Note:
        if summary.note_id in self.failing_ids:
            raise RuntimeError("read failed")
        return next(note for note in self.notes if note.note_id == summary.note_id)


def test_export_service_isolates_one_failure(tmp_path) -> None:
    source = FakeSource(
        [
            Note(note_id="_1", subject="第一条", content="<p>正文一</p>"),
            Note(note_id="_2", subject="第二条", content="<p>正文二</p>"),
        ],
        failing_ids={"_2"},
    )
    service = ExportService(source, DocxExporter())

    report = service.run(tmp_path)

    assert report.total == 2
    assert report.exported == 1
    assert report.failed == 1
    assert report.failures[0].note_id == "_2"
    assert (tmp_path / "第一条__1.docx").exists()


def test_export_service_respects_limit(tmp_path) -> None:
    source = FakeSource(
        [
            Note(note_id="_1", subject="第一条", content="正文"),
            Note(note_id="_2", subject="第二条", content="正文"),
        ]
    )

    report = ExportService(source, DocxExporter()).run(tmp_path, limit=1)

    assert report.total == 1
    assert report.exported == 1
    assert len(list(tmp_path.glob("*.docx"))) == 1
