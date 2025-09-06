"""
Timesheet Export Service for EduPulse
Handles generation of timesheet reports in Excel format
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TimesheetExportService:
    """
    Service for generating Excel timesheet reports
    """
    
    @staticmethod
    def export_teacher_timesheet(teacher=None, start_date=None, end_date=None, format='excel'):
        """
        Export teacher timesheet data to Excel format
        
        Args:
            teacher: Specific teacher (if None, exports all teachers)
            start_date: Start date for report
            end_date: End date for report  
            format: Export format ('excel' or 'csv')
            
        Returns:
            HttpResponse with Excel file
        """
        try:
            from core.models import TeacherAttendance
            from accounts.models import Staff
            
            # Set default date range if not provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)  # Last 30 days
            
            # Get attendance data
            queryset = TeacherAttendance.objects.select_related(
                'teacher', 'facility'
            ).prefetch_related('classes__course')
            
            # Filter by teacher if specified
            if teacher:
                queryset = queryset.filter(teacher=teacher)
            
            # Filter by date range
            queryset = queryset.filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            ).order_by('teacher__first_name', 'teacher__last_name', 'timestamp')
            
            # Create workbook and worksheet
            wb = openpyxl.Workbook()
            ws = wb.active
            
            # Set worksheet title
            teacher_name = f" - {teacher.get_full_name()}" if teacher else ""
            ws.title = f"Timesheet{teacher_name}"[:31]  # Excel sheet name limit
            
            # Generate the timesheet
            TimesheetExportService._generate_timesheet_worksheet(
                ws, queryset, start_date, end_date, teacher
            )
            
            # Prepare response
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # Set filename
            date_str = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
            filename = f"timesheet_{teacher_name.replace(' - ', '_').replace(' ', '_').lower()}_{date_str}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Save workbook to response
            wb.save(response)
            
            logger.info(f"Timesheet exported successfully for period {start_date} to {end_date}")
            return response
            
        except Exception as e:
            logger.error(f"Error exporting timesheet: {str(e)}")
            raise e
    
    @staticmethod
    def _generate_timesheet_worksheet(ws, queryset, start_date, end_date, teacher):
        """
        Generate the timesheet worksheet with data and formatting
        """
        # Header styling
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        # Data styling
        data_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title and header
        ws['A1'] = 'Perth Art School - Teacher Timesheet'
        ws.merge_cells('A1:H1')
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Report details
        ws['A3'] = f'Report Period: {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}'
        if teacher:
            ws['A4'] = f'Teacher: {teacher.get_full_name()}'
        ws['A5'] = f'Generated: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        
        # Column headers
        headers = [
            'Date', 'Teacher', 'Clock Type', 'Time', 'Facility', 
            'Classes', 'Duration (Hours)', 'Notes'
        ]
        
        header_row = 7
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = header_border
            cell.alignment = header_alignment
        
        # Data rows
        row = header_row + 1
        current_teacher = None
        daily_hours = {}  # Track daily hours by teacher and date
        
        for attendance in queryset:
            # Add teacher section header if changed
            if current_teacher != attendance.teacher:
                if current_teacher is not None:
                    # Add teacher summary
                    row = TimesheetExportService._add_teacher_summary(
                        ws, row, current_teacher, daily_hours
                    )
                    row += 1  # Space between teachers
                
                current_teacher = attendance.teacher
                daily_hours[current_teacher.id] = {}
            
            # Calculate duration if this is a clock-in/out pair
            duration_hours = TimesheetExportService._calculate_attendance_duration(attendance)
            
            # Track daily hours
            date_key = attendance.timestamp.date()
            if date_key not in daily_hours[current_teacher.id]:
                daily_hours[current_teacher.id][date_key] = Decimal('0')
            if duration_hours:
                daily_hours[current_teacher.id][date_key] += duration_hours
            
            # Get class names
            class_names = ', '.join([
                cls.course.name for cls in attendance.classes.all()
            ]) if attendance.classes.exists() else 'General'
            
            # Add data row
            data_row = [
                attendance.timestamp.strftime('%d/%m/%Y'),
                attendance.teacher.get_full_name(),
                attendance.get_clock_type_display(),
                attendance.timestamp.strftime('%H:%M'),
                attendance.facility.name if attendance.facility else 'N/A',
                class_names,
                float(duration_hours) if duration_hours else '',
                attendance.notes or ''
            ]
            
            for col, value in enumerate(data_row, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = data_border
                
                # Right-align duration column
                if col == 7 and value:  # Duration column
                    cell.alignment = Alignment(horizontal='right')
            
            row += 1
        
        # Add final teacher summary
        if current_teacher:
            row = TimesheetExportService._add_teacher_summary(
                ws, row, current_teacher, daily_hours
            )
        
        # Add overall summary
        row += 2
        TimesheetExportService._add_overall_summary(ws, row, queryset, daily_hours)
        
        # Adjust column widths
        column_widths = [12, 20, 15, 10, 20, 25, 15, 30]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width
    
    @staticmethod
    def _calculate_attendance_duration(attendance):
        """
        Calculate duration for attendance record based on clock in/out pairs
        """
        try:
            from core.models import TeacherAttendance
            
            # For clock_out, find matching clock_in
            if attendance.clock_type == 'clock_out':
                # Find the most recent clock_in for the same teacher on the same day
                clock_in = TeacherAttendance.objects.filter(
                    teacher=attendance.teacher,
                    clock_type='clock_in',
                    timestamp__date=attendance.timestamp.date(),
                    timestamp__lt=attendance.timestamp
                ).order_by('-timestamp').first()
                
                if clock_in:
                    duration = attendance.timestamp - clock_in.timestamp
                    hours = Decimal(str(duration.total_seconds() / 3600)).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    return hours
            
            return None
            
        except Exception as e:
            logger.warning(f"Error calculating duration for attendance {attendance.id}: {str(e)}")
            return None
    
    @staticmethod
    def _add_teacher_summary(ws, row, teacher, daily_hours):
        """
        Add summary row for a teacher
        """
        teacher_total = sum(
            sum(daily_hours.get(teacher.id, {}).values(), Decimal('0')),
        )
        
        # Teacher summary row
        ws.merge_cells(f'A{row}:E{row}')
        summary_cell = ws[f'A{row}']
        summary_cell.value = f'Total for {teacher.get_full_name()}:'
        summary_cell.font = Font(bold=True)
        summary_cell.alignment = Alignment(horizontal='right')
        
        ws[f'G{row}'] = float(teacher_total)
        ws[f'G{row}'].font = Font(bold=True)
        ws[f'G{row}'].alignment = Alignment(horizontal='right')
        
        return row + 1
    
    @staticmethod
    def _add_overall_summary(ws, row, queryset, daily_hours):
        """
        Add overall summary section
        """
        from accounts.models import Staff
        
        # Summary header
        ws[f'A{row}'] = 'SUMMARY'
        ws[f'A{row}'].font = Font(bold=True, size=12)
        row += 2
        
        # Calculate totals
        total_teachers = len(set(att.teacher.id for att in queryset))
        total_hours = sum(
            sum(teacher_daily.values(), Decimal('0'))
            for teacher_daily in daily_hours.values()
        )
        total_clock_ins = queryset.filter(clock_type='clock_in').count()
        total_clock_outs = queryset.filter(clock_type='clock_out').count()
        
        # Summary data
        summary_data = [
            ('Total Teachers:', total_teachers),
            ('Total Hours:', float(total_hours)),
            ('Total Clock Ins:', total_clock_ins),
            ('Total Clock Outs:', total_clock_outs),
        ]
        
        for label, value in summary_data:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'] = value
            row += 1
    
    @staticmethod
    def generate_monthly_summary(year, month):
        """
        Generate monthly summary report for all teachers
        """
        try:
            from core.models import TeacherAttendance
            from accounts.models import Staff
            from datetime import date
            import calendar
            
            # Get first and last day of month
            start_date = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, last_day)
            
            # Create workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f"Monthly Summary {year}-{month:02d}"
            
            # Get all attendance records for the month
            attendance_records = TeacherAttendance.objects.filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            ).select_related('teacher', 'facility').order_by('teacher', 'timestamp')
            
            # Process data
            teacher_data = {}
            for record in attendance_records:
                teacher_id = record.teacher.id
                if teacher_id not in teacher_data:
                    teacher_data[teacher_id] = {
                        'teacher': record.teacher,
                        'total_hours': Decimal('0'),
                        'days_worked': set(),
                        'total_sessions': 0
                    }
                
                # Calculate hours for clock-out records
                if record.clock_type == 'clock_out':
                    duration = TimesheetExportService._calculate_attendance_duration(record)
                    if duration:
                        teacher_data[teacher_id]['total_hours'] += duration
                        teacher_data[teacher_id]['days_worked'].add(record.timestamp.date())
                
                teacher_data[teacher_id]['total_sessions'] += 1
            
            # Generate worksheet
            TimesheetExportService._generate_monthly_summary_worksheet(
                ws, teacher_data, start_date, end_date
            )
            
            # Prepare response
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            filename = f"monthly_summary_{year}_{month:02d}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response
            
        except Exception as e:
            logger.error(f"Error generating monthly summary: {str(e)}")
            raise e
    
    @staticmethod
    def _generate_monthly_summary_worksheet(ws, teacher_data, start_date, end_date):
        """
        Generate monthly summary worksheet
        """
        # Header
        ws['A1'] = f'Perth Art School - Monthly Summary'
        ws['A1'].font = Font(bold=True, size=14)
        ws['A2'] = f'Period: {start_date.strftime("%B %Y")}'
        ws['A3'] = f'Generated: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        
        # Column headers
        headers = ['Teacher', 'Total Hours', 'Days Worked', 'Avg Hours/Day', 'Total Sessions']
        header_row = 5
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            cell.font = Font(bold=True, color='FFFFFF')
        
        # Data rows
        row = header_row + 1
        total_hours_all = Decimal('0')
        
        for teacher_info in teacher_data.values():
            teacher = teacher_info['teacher']
            total_hours = teacher_info['total_hours']
            days_worked = len(teacher_info['days_worked'])
            avg_hours = float(total_hours / days_worked) if days_worked > 0 else 0
            total_sessions = teacher_info['total_sessions']
            
            # Add row data
            ws.cell(row=row, column=1, value=teacher.get_full_name())
            ws.cell(row=row, column=2, value=float(total_hours))
            ws.cell(row=row, column=3, value=days_worked)
            ws.cell(row=row, column=4, value=round(avg_hours, 2))
            ws.cell(row=row, column=5, value=total_sessions)
            
            total_hours_all += total_hours
            row += 1
        
        # Totals row
        row += 1
        ws.cell(row=row, column=1, value='TOTAL:').font = Font(bold=True)
        ws.cell(row=row, column=2, value=float(total_hours_all)).font = Font(bold=True)
        
        # Adjust column widths
        column_widths = [25, 15, 15, 15, 15]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width