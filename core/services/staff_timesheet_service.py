"""
Staff Timesheet Panel Service for EduPulse
Handles timesheet data processing for staff detail pages
"""
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StaffTimesheetService:
    """
    Service for processing staff timesheet data and clock in/out pairing
    """
    
    @staticmethod
    def get_staff_timesheet_data(staff, start_date=None, end_date=None):
        """
        Get comprehensive timesheet data for a staff member
        
        Args:
            staff: Staff instance
            start_date: Start date for filtering (defaults to last 30 days)
            end_date: End date for filtering (defaults to today)
            
        Returns:
            Dict containing paired records, summary statistics, and raw data
        """
        try:
            from core.models import TeacherAttendance
            
            # Set default date range if not provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Get TeacherAttendance records (primary source)
            teacher_attendance = TeacherAttendance.objects.filter(
                teacher=staff,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date
            ).select_related('facility').prefetch_related('classes__course').order_by('timestamp')
            
            # Process and pair the records
            paired_records = StaffTimesheetService._pair_attendance_records(
                teacher_attendance
            )
            
            # Calculate summary statistics
            summary = StaffTimesheetService._calculate_summary(paired_records)
            
            return {
                'paired_records': paired_records,
                'summary': summary,
                'raw_teacher_attendance': list(teacher_attendance),
                'raw_clock_records': [],
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting timesheet data for staff {staff.id}: {str(e)}")
            return {
                'paired_records': [],
                'summary': {'total_hours': 0, 'total_days': 0, 'avg_hours_per_day': 0},
                'raw_teacher_attendance': [],
                'raw_clock_records': [],
                'date_range': {'start_date': start_date, 'end_date': end_date},
                'error': str(e)
            }
    
    @staticmethod
    def _pair_attendance_records(teacher_attendance):
        """
        Pair clock in/out records to create work sessions
        """
        paired_records = []
        
        # Group records by date
        records_by_date = {}
        
        # Add TeacherAttendance records
        for record in teacher_attendance:
            date_key = record.timestamp.date()
            if date_key not in records_by_date:
                records_by_date[date_key] = {'teacher_attendance': []}
            records_by_date[date_key]['teacher_attendance'].append(record)
        
        # Process each date
        for date, records in records_by_date.items():
            date_pairs = StaffTimesheetService._pair_records_for_date(
                date, records['teacher_attendance']
            )
            paired_records.extend(date_pairs)
        
        # Sort by date and time
        paired_records.sort(key=lambda x: x['date'])
        
        return paired_records
    
    @staticmethod
    def _pair_records_for_date(date, teacher_attendance):
        """
        Pair records for a specific date
        """
        pairs = []
        
        # First, try to pair TeacherAttendance records (preferred)
        teacher_pairs = StaffTimesheetService._pair_teacher_attendance(date, teacher_attendance)
        pairs.extend(teacher_pairs)
        
        return pairs
    
    @staticmethod
    def _pair_teacher_attendance(date, records):
        """
        Pair TeacherAttendance records (clock_in with clock_out)
        """
        pairs = []
        clock_ins = [r for r in records if r.clock_type == 'clock_in']
        clock_outs = [r for r in records if r.clock_type == 'clock_out']
        
        # Match clock_ins with clock_outs
        for clock_in in clock_ins:
            # Find the next clock_out after this clock_in
            matching_clock_out = None
            for clock_out in clock_outs:
                if (clock_out.timestamp > clock_in.timestamp and 
                    clock_out.facility_id == clock_in.facility_id):
                    matching_clock_out = clock_out
                    break
            
            # Get associated classes
            classes = list(clock_in.classes.all())
            if matching_clock_out:
                # Add classes from clock_out as well
                classes.extend(list(matching_clock_out.classes.all()))
                # Remove duplicates
                classes = list({cls.id: cls for cls in classes}.values())
            
            # Calculate duration
            duration_hours = None
            if matching_clock_out:
                duration = matching_clock_out.timestamp - clock_in.timestamp
                duration_hours = duration.total_seconds() / 3600
                # Remove the matched clock_out from the list
                clock_outs.remove(matching_clock_out)
            
            pairs.append({
                'date': date,
                'clock_in': clock_in,
                'clock_out': matching_clock_out,
                'clock_in_time': clock_in.timestamp.time(),
                'clock_out_time': matching_clock_out.timestamp.time() if matching_clock_out else None,
                'duration_hours': duration_hours,
                'facility': clock_in.facility,
                'classes': classes,
                'source': 'teacher_attendance',
                'notes': clock_in.notes,
                'is_complete': matching_clock_out is not None
            })
        
        # Handle unmatched clock_outs
        for clock_out in clock_outs:
            classes = list(clock_out.classes.all())
            pairs.append({
                'date': date,
                'clock_in': None,
                'clock_out': clock_out,
                'clock_in_time': None,
                'clock_out_time': clock_out.timestamp.time(),
                'duration_hours': None,
                'facility': clock_out.facility,
                'classes': classes,
                'source': 'teacher_attendance',
                'notes': clock_out.notes,
                'is_complete': False,
                'anomaly': 'clock_out_without_clock_in'
            })
        
        return pairs
    
    
    @staticmethod
    def _calculate_summary(paired_records):
        """
        Calculate summary statistics from paired records
        """
        total_hours = 0
        completed_sessions = 0
        unique_dates = set()
        
        for record in paired_records:
            if record['duration_hours'] is not None:
                total_hours += record['duration_hours']
                completed_sessions += 1
            unique_dates.add(record['date'])
        
        total_days = len(unique_dates)
        avg_hours_per_day = total_hours / total_days if total_days > 0 else 0
        
        return {
            'total_hours': round(total_hours, 2),
            'total_days': total_days,
            'completed_sessions': completed_sessions,
            'incomplete_sessions': len(paired_records) - completed_sessions,
            'avg_hours_per_day': round(avg_hours_per_day, 2)
        }
    
    @staticmethod
    def format_duration(hours):
        """
        Format duration in hours to human-readable format
        """
        if hours is None:
            return "Incomplete"
        
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes}m"
        else:
            whole_hours = int(hours)
            minutes = int((hours - whole_hours) * 60)
            if minutes > 0:
                return f"{whole_hours}h {minutes}m"
            else:
                return f"{whole_hours}h"
    
    @staticmethod
    def get_classes_display(classes):
        """
        Format classes for display
        """
        if not classes:
            return "General Work"
        
        class_names = [cls.course.name for cls in classes]
        if len(class_names) == 1:
            return class_names[0]
        elif len(class_names) <= 3:
            return ", ".join(class_names)
        else:
            return f"{class_names[0]} + {len(class_names)-1} more"
    
    @staticmethod
    def get_all_staff_timesheet_data(staff_queryset, start_date=None, end_date=None):
        """
        Get timesheet data for all staff members with overall summary
        
        Args:
            staff_queryset: QuerySet of Staff instances
            start_date: Start date for filtering (defaults to last 30 days)
            end_date: End date for filtering (defaults to today)
            
        Returns:
            Dict containing overall summary and individual staff summaries
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Set default date range if not provided
            if not end_date:
                end_date = timezone.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            staff_summaries = []
            overall_total_hours = 0
            overall_total_sessions = 0
            active_staff_count = 0
            
            # Process each staff member
            for staff in staff_queryset:
                # Get individual timesheet data
                timesheet_data = StaffTimesheetService.get_staff_timesheet_data(
                    staff, start_date, end_date
                )
                
                # Calculate staff summary
                paired_records = timesheet_data.get('paired_records', [])
                total_hours = sum(record.get('duration_hours', 0) for record in paired_records)
                sessions = len(paired_records)
                working_days = len(set(record['date'] for record in paired_records if record.get('duration_hours', 0) > 0))
                average_hours_per_day = total_hours / working_days if working_days > 0 else 0
                
                # Only include staff with activity
                if sessions > 0:
                    staff_summaries.append({
                        'staff': staff,
                        'total_hours': round(total_hours, 2),
                        'working_days': working_days,
                        'sessions': sessions,
                        'average_hours_per_day': round(average_hours_per_day, 2),
                        'detailed_records': paired_records  # Optional for detailed view
                    })
                    
                    overall_total_hours += total_hours
                    overall_total_sessions += sessions
                    active_staff_count += 1
            
            # Calculate overall summary
            average_hours_per_staff = overall_total_hours / active_staff_count if active_staff_count > 0 else 0
            
            overall_summary = {
                'total_hours': round(overall_total_hours, 2),
                'active_staff_count': active_staff_count,
                'total_sessions': overall_total_sessions,
                'average_hours_per_staff': round(average_hours_per_staff, 2)
            }
            
            return {
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'overall_summary': overall_summary,
                'staff_summaries': staff_summaries
            }
            
        except Exception as e:
            logger.error(f"Error getting all staff timesheet data: {str(e)}")
            return {
                'date_range': {
                    'start_date': start_date or timezone.now().date() - timedelta(days=30),
                    'end_date': end_date or timezone.now().date()
                },
                'overall_summary': {
                    'total_hours': 0,
                    'active_staff_count': 0,
                    'total_sessions': 0,
                    'average_hours_per_staff': 0
                },
                'staff_summaries': []
            }

