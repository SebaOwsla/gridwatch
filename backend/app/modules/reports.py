"""Detailed and aggregated reports for simulated electrical telemetry."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID
from xml.sax.saxutils import escape

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.api.dependencies import CurrentUser, SessionDep
from app.core.time_window import validated_window
from app.db.models import Equipment, Measurement
from app.modules.audit import record_audit


router = APIRouter(prefix="/reports", tags=["reports"])
MAX_REPORT_ROWS = 5000

METRICS = (
    ("voltage_l1_v", "Voltaje L1", "V"),
    ("voltage_l2_v", "Voltaje L2", "V"),
    ("voltage_l3_v", "Voltaje L3", "V"),
    ("current_l1_a", "Corriente L1", "A"),
    ("current_l2_a", "Corriente L2", "A"),
    ("current_l3_a", "Corriente L3", "A"),
    ("active_power_kw", "Potencia activa", "kW"),
    ("frequency_hz", "Frecuencia", "Hz"),
)


@dataclass(frozen=True)
class MetricSummary:
    minimum: float | None
    average: float | None
    maximum: float | None


@dataclass(frozen=True)
class ReportSummary:
    total_samples: int
    valid_samples: int
    metrics: dict[str, MetricSummary]


def safe_excel_text(value: str) -> str:
    """Keep asset names from becoming formulas when a workbook is opened."""
    return "'" + value if value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) else value


def build_excel(equipment: Equipment, rows: list[Measurement], start: datetime, end: datetime) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Mediciones"
    sheet.append(["GridWatch - mediciones simuladas"])
    sheet.append(["Equipo", safe_excel_text(equipment.code), safe_excel_text(equipment.name)])
    sheet.append(["Periodo UTC", start.isoformat(), end.isoformat()])
    headers = ["Fecha UTC", "Calidad"] + [name + " (" + unit + ")" for _, name, unit in METRICS]
    sheet.append(headers)
    for row in rows:
        timestamp = row.measured_at.astimezone(timezone.utc).replace(tzinfo=None)
        sheet.append([timestamp, row.quality] + [getattr(row, field) for field, _, _ in METRICS])
        sheet.cell(sheet.max_row, 1).number_format = "yyyy-mm-dd hh:mm:ss"

    for cell in sheet[4]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="16324F")
    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:J{max(sheet.max_row, 4)}"
    sheet.column_dimensions["A"].width = 22
    for letter in "BCDEFGHIJ":
        sheet.column_dimensions[letter].width = 19

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_pdf(equipment: Equipment, summary: ReportSummary, start: datetime, end: datetime) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=(210 * mm, 297 * mm),
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="GridWatch - resumen eléctrico",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("GridWatch - resumen eléctrico", styles["Title"]),
        Spacer(1, 6 * mm),
        Paragraph("Datos simulados; sin conexión a equipos reales.", styles["Normal"]),
        Paragraph(
            f"Equipo: {escape(equipment.code)} - {escape(equipment.name)}",
            styles["Normal"],
        ),
        Paragraph(f"Periodo UTC: {start.isoformat()} a {end.isoformat()}", styles["Normal"]),
        Paragraph(
            f"Muestras: {summary.total_samples}; válidas: {summary.valid_samples}",
            styles["Normal"],
        ),
        Spacer(1, 7 * mm),
    ]
    data = [["Magnitud", "Mínimo", "Promedio", "Máximo", "Unidad"]]
    for field, label, unit in METRICS:
        stats = summary.metrics[field]
        if stats.minimum is not None and stats.average is not None and stats.maximum is not None:
            data.append([
                label, f"{stats.minimum:.2f}", f"{stats.average:.2f}", f"{stats.maximum:.2f}", unit,
            ])
    if len(data) == 1:
        story.append(Paragraph("Sin lecturas válidas para este periodo.", styles["Normal"]))
    else:
        table = Table(data, colWidths=[55 * mm, 30 * mm, 30 * mm, 30 * mm, 24 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8D3DC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F8")]),
        ]))
        story.append(table)
    document.build(story)
    return output.getvalue()


def build_summary_excel(
    equipment: Equipment,
    summary: ReportSummary,
    buckets: list[dict],
    start: datetime,
    end: datetime,
    bucket_minutes: int,
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Resumen"
    sheet.append(["GridWatch - resumen eléctrico simulado"])
    sheet.append(["Equipo", safe_excel_text(equipment.code), safe_excel_text(equipment.name)])
    sheet.append(["Periodo UTC", start.isoformat(), end.isoformat()])
    sheet.append(["Muestras", summary.total_samples, "Válidas", summary.valid_samples])
    sheet.append(["Intervalo", f"{bucket_minutes} minutos"])
    sheet.append([])
    sheet.append(["Magnitud", "Mínimo", "Promedio", "Máximo", "Unidad"])
    for field, label, unit in METRICS:
        stats = summary.metrics[field]
        sheet.append([label, stats.minimum, stats.average, stats.maximum, unit])
    for cell in sheet[7]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="16324F")
    sheet.column_dimensions["A"].width = 25
    for letter in "BCDE":
        sheet.column_dimensions[letter].width = 21

    intervals = workbook.create_sheet("Intervalos")
    intervals.append(["Inicio UTC", "Muestras válidas"] + [f"{label} ({unit})" for _, label, unit in METRICS])
    for bucket in buckets:
        instant = bucket["bucket_start"].astimezone(timezone.utc).replace(tzinfo=None)
        intervals.append([instant, bucket["sample_count"]] + [bucket[field] for field, _, _ in METRICS])
        intervals.cell(intervals.max_row, 1).number_format = "yyyy-mm-dd hh:mm:ss"
    for cell in intervals[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="16324F")
    intervals.freeze_panes = "C2"
    intervals.auto_filter.ref = f"A1:J{max(intervals.max_row, 1)}"
    intervals.column_dimensions["A"].width = 22
    for letter in "BCDEFGHIJ":
        intervals.column_dimensions[letter].width = 20

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def report_context(
    session: SessionDep, equipment_id: UUID, start: datetime, end: datetime
) -> tuple[Equipment, datetime, datetime]:
    try:
        start_utc, end_utc = validated_window(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment, start_utc, end_utc


def report_data(
    session: SessionDep, equipment_id: UUID, start: datetime, end: datetime
) -> tuple[Equipment, list[Measurement], datetime, datetime]:
    equipment, start_utc, end_utc = report_context(session, equipment_id, start, end)
    query = (
        sa.select(Measurement)
        .where(
            Measurement.equipment_id == equipment_id,
            Measurement.measured_at >= start_utc,
            Measurement.measured_at < end_utc,
        )
        .order_by(Measurement.measured_at)
        .limit(MAX_REPORT_ROWS + 1)
    )
    rows = list(session.scalars(query))
    if len(rows) > MAX_REPORT_ROWS:
        raise HTTPException(
            status_code=422,
            detail="El detalle supera 5000 muestras. Acorta el periodo o usa Excel resumido.",
        )
    return equipment, rows, start_utc, end_utc


def report_summary_data(
    session: SessionDep, equipment_id: UUID, start: datetime, end: datetime
) -> tuple[Equipment, ReportSummary, datetime, datetime]:
    equipment, start_utc, end_utc = report_context(session, equipment_id, start, end)
    filters = (
        Measurement.equipment_id == equipment_id,
        Measurement.measured_at >= start_utc,
        Measurement.measured_at < end_utc,
    )
    valid = Measurement.quality == "valid"
    statement = sa.select(
        sa.func.count().label("total_samples"),
        sa.func.count().filter(valid).label("valid_samples"),
        *(
            aggregate(getattr(Measurement, field)).filter(valid).label(f"{field}_{name}")
            for field, _, _ in METRICS
            for name, aggregate in (("min", sa.func.min), ("avg", sa.func.avg), ("max", sa.func.max))
        ),
    ).where(*filters)
    values = session.execute(statement).mappings().one()
    summary = ReportSummary(
        total_samples=values["total_samples"],
        valid_samples=values["valid_samples"],
        metrics={
            field: MetricSummary(
                minimum=values[f"{field}_min"],
                average=values[f"{field}_avg"],
                maximum=values[f"{field}_max"],
            )
            for field, _, _ in METRICS
        },
    )
    return equipment, summary, start_utc, end_utc


def report_buckets(
    session: SessionDep, equipment_id: UUID, start: datetime, end: datetime
) -> tuple[list[dict], int]:
    duration = end - start
    bucket_minutes = 5 if duration <= timedelta(days=1) else 60 if duration <= timedelta(days=7) else 360
    bucket = sa.func.time_bucket(
        sa.cast(sa.literal(f"{bucket_minutes} minutes"), sa.Interval()),
        Measurement.measured_at,
    ).label("bucket_start")
    query = (
        sa.select(
            bucket,
            sa.func.count().label("sample_count"),
            *(sa.func.avg(getattr(Measurement, field)).label(field) for field, _, _ in METRICS),
        )
        .where(
            Measurement.equipment_id == equipment_id,
            Measurement.measured_at >= start,
            Measurement.measured_at < end,
            Measurement.quality == "valid",
        )
        .group_by(bucket)
        .order_by(bucket)
        .limit(350)
    )
    return [dict(row) for row in session.execute(query).mappings()], bucket_minutes


@router.get(
    "/measurements.xlsx",
    response_class=Response,
    responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}},
)
def export_excel(
    equipment_id: UUID,
    start: datetime,
    end: datetime,
    session: SessionDep,
    user: CurrentUser,
) -> Response:
    equipment, rows, start_utc, end_utc = report_data(session, equipment_id, start, end)
    content = build_excel(equipment, rows, start_utc, end_utc)
    record_audit(
        session, actor_id=user.id, action="report.exported", entity_type="equipment",
        entity_id=equipment_id,
        details={"format": "xlsx", "rows": len(rows), "start": start_utc.isoformat(), "end": end_utc.isoformat()},
    )
    session.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="gridwatch-{equipment_id}.xlsx"'},
    )


@router.get(
    "/summary.xlsx",
    response_class=Response,
    responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}},
)
def export_summary_excel(
    equipment_id: UUID,
    start: datetime,
    end: datetime,
    session: SessionDep,
    user: CurrentUser,
) -> Response:
    equipment, summary, start_utc, end_utc = report_summary_data(session, equipment_id, start, end)
    buckets, bucket_minutes = report_buckets(session, equipment_id, start_utc, end_utc)
    content = build_summary_excel(equipment, summary, buckets, start_utc, end_utc, bucket_minutes)
    record_audit(
        session, actor_id=user.id, action="report.exported", entity_type="equipment",
        entity_id=equipment_id,
        details={
            "format": "xlsx-summary", "rows": summary.total_samples,
            "valid_rows": summary.valid_samples, "bucket_minutes": bucket_minutes,
            "start": start_utc.isoformat(), "end": end_utc.isoformat(),
        },
    )
    session.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="gridwatch-resumen-{equipment_id}.xlsx"'},
    )


@router.get("/measurements.pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_pdf(
    equipment_id: UUID,
    start: datetime,
    end: datetime,
    session: SessionDep,
    user: CurrentUser,
) -> Response:
    equipment, summary, start_utc, end_utc = report_summary_data(session, equipment_id, start, end)
    content = build_pdf(equipment, summary, start_utc, end_utc)
    record_audit(
        session, actor_id=user.id, action="report.exported", entity_type="equipment",
        entity_id=equipment_id,
        details={
            "format": "pdf", "rows": summary.total_samples, "valid_rows": summary.valid_samples,
            "start": start_utc.isoformat(), "end": end_utc.isoformat(),
        },
    )
    session.commit()
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="gridwatch-{equipment_id}.pdf"'},
    )
