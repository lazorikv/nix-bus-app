"""PDF ticket generation using ReportLab, stored in MinIO/S3."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Order, Trip
from app.storage import upload_bytes


def render_ticket_pdf(order: Order, trip: Trip) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Ticket #{order.id}")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Bus Ticket", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Order #{order.id}", styles["Heading2"]))
    story.append(Paragraph(f"Trip: {trip.name}", styles["Normal"]))
    story.append(Paragraph(f"Status: {order.status.value}", styles["Normal"]))
    story.append(Paragraph(f"Total price: {order.price}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    route = trip.route or []
    if route:
        origin = route[0].get("city_name", "?")
        destination = route[-1].get("city_name", "?")
        story.append(Paragraph(f"Route: {origin} → {destination}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Passengers", styles["Heading3"]))
    rows = [["#", "Name", "Age", "Email", "Price"]]
    for idx, p in enumerate(order.passengers, start=1):
        rows.append(
            [
                str(idx),
                f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                str(p.get("age", "")),
                p.get("email", ""),
                str(p.get("ticket_price", "")),
            ]
        )
    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()


def generate_and_store_ticket(order: Order, trip: Trip) -> str:
    """Render the ticket PDF, upload it to object storage, and return the object key."""
    pdf_bytes = render_ticket_pdf(order, trip)
    key = f"tickets/order-{order.id}.pdf"
    upload_bytes(key, pdf_bytes, content_type="application/pdf")
    return key
