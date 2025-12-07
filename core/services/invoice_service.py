"""
PDF invoice generation utilities for enrollment notifications.
"""
import logging
from decimal import Decimal
from io import BytesIO
from typing import Optional, Dict

from django.utils import timezone

from core.models import OrganisationSettings

logger = logging.getLogger(__name__)


class EnrollmentInvoiceService:
    """Generate simple PDF invoices for enrollments."""

    @staticmethod
    def generate_invoice_pdf(enrollment, fee_breakdown: Optional[Dict] = None) -> Optional[Dict[str, bytes]]:
        """
        Build a lightweight PDF invoice for an enrollment.

        Returns a dict with filename, content, and mimetype or None if generation fails.
        """
        try:
            from fpdf import FPDF
        except Exception as exc:  # pragma: no cover - defensive import guard
            logger.error("fpdf2 is required to generate invoices: %s", exc)
            return None

        try:
            org_settings = OrganisationSettings.get_instance()
            student = enrollment.student
            course = enrollment.course
            issue_date = timezone.now()
            reference = enrollment.get_reference_id()

            if fee_breakdown:
                course_fee = Decimal(str(fee_breakdown.get('course_fee', 0)))
                registration_fee = Decimal(str(fee_breakdown.get('registration_fee', 0)))
                total_fee = Decimal(str(fee_breakdown.get('total_fee', course_fee + registration_fee)))
            else:
                course_fee = enrollment.course_fee
                registration_fee = enrollment.registration_fee
                total_fee = enrollment.get_total_fee()

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "Invoice", ln=True)
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 8, f"Issue Date: {issue_date.strftime('%d %b %Y')}", ln=True)
            pdf.cell(0, 8, f"Invoice #: {reference}", ln=True)
            abn_number = (org_settings.abn_number or "").strip()
            if abn_number:
                pdf.cell(0, 8, f"ABN: {abn_number}", ln=True)
            pdf.ln(6)

            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Bill To", ln=True)
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 6, student.get_full_name(), ln=True)
            pdf.cell(0, 6, student.contact_email or "No email provided", ln=True)
            pdf.ln(6)

            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Course", ln=True)
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 6, course.name, ln=True)
            if course.start_date:
                pdf.cell(0, 6, f"Start Date: {course.start_date.strftime('%d %b %Y')}", ln=True)
            pdf.ln(6)

            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(110, 8, "Description", border=1)
            pdf.cell(0, 8, "Amount (AUD)", border=1, ln=True)

            pdf.set_font("Helvetica", size=12)
            pdf.cell(110, 8, "Course fee", border=1)
            pdf.cell(0, 8, f"${course_fee:.2f}", border=1, ln=True)
            if registration_fee and registration_fee > 0:
                pdf.cell(110, 8, "Registration fee", border=1)
                pdf.cell(0, 8, f"${registration_fee:.2f}", border=1, ln=True)

            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(110, 8, "Total due", border=1)
            pdf.cell(0, 8, f"${total_fee:.2f}", border=1, ln=True)

            pdf.ln(10)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Payment Details", ln=True)
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 6, f"Account Name: {org_settings.bank_account_name}", ln=True)
            pdf.cell(0, 6, f"BSB: {org_settings.bank_bsb}", ln=True)
            pdf.cell(0, 6, f"Account Number: {org_settings.bank_account_number}", ln=True)
            pdf.cell(0, 6, f"Reference: {reference}", ln=True)

            pdf.ln(10)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(
                0,
                6,
                "Please include the reference exactly when paying so we can match your payment quickly."
            )

            # fpdf2 returns a bytearray when dest="S"; convert to immutable bytes for attachments
            pdf_bytes = bytes(pdf.output(dest="S"))
            return {
                'filename': f"Invoice-{reference}.pdf",
                'content': pdf_bytes,
                'mimetype': 'application/pdf'
            }
        except Exception as exc:
            logger.error("Failed to generate invoice PDF for enrollment %s: %s", enrollment.id, exc)
            return None
