from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.timezone import day_bounds_utc
from app.domain.repositories.bicycle_repository import BicycleRepository
from app.domain.repositories.client_repository import ClientRepository
from app.domain.repositories.loan_repository import LoanRepository

_DETAIL_STATUS_LABELS = {"on_loan": "Prestada", "returned": "Entregada"}


class ReportService:
    def __init__(
        self,
        loan_repository: LoanRepository,
        client_repository: ClientRepository,
        bicycle_repository: BicycleRepository,
    ):
        self.loan_repository = loan_repository
        self.client_repository = client_repository
        self.bicycle_repository = bicycle_repository

    def generate_loans_report(self, start_date: date, end_date: date) -> bytes:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date")

        start_datetime = day_bounds_utc(start_date)[0]
        end_datetime = day_bounds_utc(end_date)[1]
        loans = self.loan_repository.list_by_date_range(start_datetime, end_datetime)

        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Reporte de préstamos - JAC Medellín", styles["Title"]),
            Paragraph(f"Periodo: {start_date.isoformat()} a {end_date.isoformat()}", styles["Normal"]),
            Spacer(1, 1 * cm),
        ]

        if not loans:
            story.append(Paragraph("No se registraron préstamos en el periodo seleccionado.", styles["Normal"]))
        else:
            for loan in loans:
                story.append(Paragraph(f"Préstamo #{loan.id}", styles["Heading3"]))
                story.append(self._loan_table(loan))
                story.append(Spacer(1, 0.5 * cm))

        document.build(story)
        return buffer.getvalue()

    def _loan_table(self, loan) -> Table:
        client = self.client_repository.get_by_id(loan.client_id)
        details = self.loan_repository.list_details_by_loan(loan.id)
        bicycle_lines = []
        for detail in details:
            bicycle = self.bicycle_repository.get_by_id(detail.bicycle_id)
            code = bicycle.code if bicycle else f"#{detail.bicycle_id}"
            bicycle_lines.append(f"{code} - {_DETAIL_STATUS_LABELS[detail.status.value]}")

        rows = [
            ["Cliente", client.full_name],
            ["Documento", client.document],
            ["Celular", client.phone],
            ["Fecha y hora", loan.loan_datetime.isoformat(sep=" ", timespec="minutes")],
            ["Bicicletas", "\n".join(bicycle_lines) if bicycle_lines else "Sin bicicletas"],
        ]
        table = Table(rows, colWidths=[4 * cm, 10 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        return table
