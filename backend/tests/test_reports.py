"""Export real workbook and PDF bytes without a database service."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

from openpyxl import load_workbook

from app.db.models import Equipment, Measurement
from app.modules.reports import (
    METRICS, MetricSummary, ReportSummary, build_excel, build_pdf, build_summary_excel,
)


def test_report_files_are_valid_and_avoid_excel_formulas() -> None:
    start = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
    equipment = Equipment(id=uuid4(), code="TR-01", name="=SUM(1,1)")
    rows = [
        Measurement(
            equipment_id=equipment.id, measured_at=start + timedelta(minutes=1),
            quality="valid", voltage_l1_v=220.5, active_power_kw=-5.0,
        ),
        Measurement(
            equipment_id=equipment.id, measured_at=start + timedelta(minutes=2),
            quality="invalid", voltage_l1_v=230.0,
        ),
    ]

    workbook_bytes = build_excel(equipment, rows, start, start + timedelta(hours=1))
    sheet = load_workbook(BytesIO(workbook_bytes), read_only=True).active
    assert sheet["C2"].value.startswith("'=")
    assert sheet["C5"].value == 220.5
    assert sheet["B6"].value == "invalid"

    summary = ReportSummary(
        total_samples=2,
        valid_samples=1,
        metrics={
            field: MetricSummary(
                minimum=getattr(rows[0], field),
                average=getattr(rows[0], field),
                maximum=getattr(rows[0], field),
            )
            for field, _, _ in METRICS
        },
    )
    pdf_bytes = build_pdf(equipment, summary, start, start + timedelta(hours=1))
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes[-20:]

    bucket = {
        "bucket_start": start,
        "sample_count": 1,
        **{field: getattr(rows[0], field) for field, _, _ in METRICS},
    }
    summary_bytes = build_summary_excel(
        equipment, summary, [bucket], start, start + timedelta(hours=1), 5,
    )
    workbook = load_workbook(BytesIO(summary_bytes), read_only=True)
    assert workbook.sheetnames == ["Resumen", "Intervalos"]
    assert workbook["Resumen"]["C2"].value.startswith("'=")
    assert workbook["Resumen"]["D4"].value == 1
    assert workbook["Intervalos"]["C2"].value == 220.5
