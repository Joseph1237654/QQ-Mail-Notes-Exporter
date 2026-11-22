from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from qq_notebook_exporter.docx_exporter import DocxExporter
from qq_notebook_exporter.gateway import NoteSource
from qq_notebook_exporter.models import NoteSummary

ProgressCallback = Callable[[int, int, NoteSummary, str], None]


@dataclass(frozen=True, slots=True)
class ExportFailure:
    note_id: str
    title: str
    message: str


@dataclass(slots=True)
class ExportReport:
    total: int = 0
    exported: int = 0
    skipped: int = 0
    failures: list[ExportFailure] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return len(self.failures)

    @property
    def successful(self) -> bool:
        return not self.failures


class ExportService:
    def __init__(self, source: NoteSource, exporter: DocxExporter) -> None:
        self.source = source
        self.exporter = exporter

    def run(
        self,
        output_dir: Path,
        *,
        limit: int | None = None,
        overwrite: bool = False,
        progress: ProgressCallback | None = None,
    ) -> ExportReport:
        summaries = self.source.list_notes()
        if limit is not None:
            summaries = summaries[: max(0, limit)]

        report = ExportReport(total=len(summaries))
        for index, summary in enumerate(summaries, start=1):
            if not overwrite and self.exporter.has_valid_output(
                output_dir,
                summary.display_title,
                summary.note_id,
            ):
                report.skipped += 1
                if progress is not None:
                    progress(index, len(summaries), summary, "已存在")
                continue
            try:
                note = self.source.read_note(summary)
                outcome = self.exporter.export_note(
                    note,
                    output_dir,
                    overwrite=overwrite,
                )
                if outcome.created:
                    report.exported += 1
                    status = "已导出"
                else:
                    report.skipped += 1
                    status = "已存在"
            except Exception as exc:
                report.failures.append(
                    ExportFailure(
                        note_id=summary.note_id,
                        title=summary.display_title,
                        message=str(exc) or exc.__class__.__name__,
                    )
                )
                status = "失败"

            if progress is not None:
                progress(index, len(summaries), summary, status)

        return report
