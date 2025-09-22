import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from students.models import Student, StudentActivity
from enrollment.models import Enrollment
from enrollment.models import Attendance
from django.utils import timezone


class Command(BaseCommand):
    help = '根据ID或ID范围删除学生记录，包含安全检查和级联清理'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=int,
            help='要删除的单个学生ID'
        )
        parser.add_argument(
            '--range',
            type=str,
            help='要删除的ID范围 (格式: start-end, 例如: 10-20)'
        )
        parser.add_argument(
            '--ids',
            type=str,
            help='要删除的多个ID，用逗号分隔 (例如: 1,3,5,7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览模式：显示将要删除的内容但不实际删除'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制删除，跳过确认提示'
        )
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='包含非活跃学生 (默认: 只处理活跃学生)'
        )
        parser.add_argument(
            '--reason',
            type=str,
            help='删除原因 (用于记录和审计)'
        )

    def handle(self, *args, **options):
        student_id = options.get('id')
        id_range = options.get('range')
        ids_str = options.get('ids')
        dry_run = options['dry_run']
        force = options['force']
        include_inactive = options['include_inactive']
        reason = options.get('reason', '通过管理命令删除')

        # 验证参数
        param_count = sum(bool(x) for x in [student_id, id_range, ids_str])
        if param_count != 1:
            raise CommandError('必须指定且仅指定以下参数之一: --id, --range, 或 --ids')

        if dry_run:
            self.stdout.write(self.style.WARNING('预览模式 - 不会实际删除任何数据'))

        try:
            # 获取要删除的学生ID列表
            if student_id:
                student_ids = [student_id]
            elif id_range:
                student_ids = self.parse_id_range(id_range)
            else:
                student_ids = self.parse_ids_list(ids_str)

            # 获取要删除的学生
            students_to_delete = self.get_students_to_delete(student_ids, include_inactive)

            if not students_to_delete:
                self.stdout.write(self.style.WARNING('没有找到符合条件的学生'))
                return

            # 显示删除预览
            related_data = self.analyze_related_data(students_to_delete)
            self.show_deletion_preview(students_to_delete, related_data)

            # 执行安全检查
            warnings = self.perform_safety_checks(students_to_delete, related_data)
            if warnings:
                self.show_warnings(warnings)

            # 确认删除 (除非是强制模式或预览模式)
            if not dry_run and not force:
                if not self.confirm_deletion(len(students_to_delete), related_data):
                    self.stdout.write('删除操作已取消')
                    return

            # 执行删除
            if not dry_run:
                deleted_count, summary = self.delete_students(students_to_delete, reason)
                self.show_deletion_summary(deleted_count, summary)
            else:
                self.stdout.write(
                    self.style.WARNING(f'预览：将删除 {len(students_to_delete)} 名学生')
                )

        except Exception as e:
            raise CommandError(f'删除过程中发生错误: {str(e)}')

    def parse_id_range(self, range_str):
        """解析ID范围字符串为ID列表"""
        try:
            if '-' not in range_str:
                raise ValueError('范围格式应为 start-end (例如: 10-20)')

            start_str, end_str = range_str.split('-', 1)
            start_id = int(start_str.strip())
            end_id = int(end_str.strip())

            if start_id > end_id:
                raise ValueError('起始ID不能大于结束ID')

            if end_id - start_id > 1000:
                raise ValueError('范围太大 (最大1000个学生)')

            return list(range(start_id, end_id + 1))

        except ValueError as e:
            raise CommandError(f'无效的范围格式: {str(e)}')

    def parse_ids_list(self, ids_str):
        """解析逗号分隔的ID列表"""
        try:
            ids = []
            for id_str in ids_str.split(','):
                id_val = int(id_str.strip())
                if id_val <= 0:
                    raise ValueError(f'无效的ID: {id_val}')
                ids.append(id_val)

            if len(ids) > 1000:
                raise ValueError('ID列表太长 (最大1000个)')

            return list(set(ids))  # 去重

        except ValueError as e:
            raise CommandError(f'无效的ID列表: {str(e)}')

    def get_students_to_delete(self, student_ids, include_inactive):
        """获取符合条件的学生记录"""
        queryset = Student.objects.filter(id__in=student_ids)

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset.select_related('level').prefetch_related(
            'enrollments', 'activities', 'tags', 'attendances'
        ).order_by('id')

    def analyze_related_data(self, students):
        """分析相关数据"""
        related_data = {
            'total_enrollments': 0,
            'active_enrollments': 0,
            'total_activities': 0,
            'total_attendances': 0,
            'recent_activities': 0,
            'recent_attendances': 0,
        }

        cutoff_date = timezone.now() - timezone.timedelta(days=30)

        for student in students:
            enrollments = student.enrollments.all()
            activities = student.activities.all()
            attendances = student.attendances.all()

            related_data['total_enrollments'] += enrollments.count()
            related_data['active_enrollments'] += enrollments.filter(
                status__in=['pending', 'confirmed', 'waitlisted']
            ).count()
            related_data['total_activities'] += activities.count()
            related_data['total_attendances'] += attendances.count()
            related_data['recent_activities'] += activities.filter(
                created_at__gte=cutoff_date
            ).count()
            related_data['recent_attendances'] += attendances.filter(
                attendance_time__gte=cutoff_date
            ).count()

        return related_data

    def show_deletion_preview(self, students, related_data):
        """显示删除预览"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING('即将删除的学生:'))
        self.stdout.write('=' * 60)

        for student in students:
            status = "活跃" if student.is_active else "非活跃"
            level = student.level.name if student.level else "无等级"
            age = student.get_age()
            age_str = f" (年龄: {age})" if age else ""

            self.stdout.write(
                f"ID: {student.id} | {student.get_full_name()}{age_str} | "
                f"状态: {status} | 等级: {level}"
            )

            if student.contact_email:
                self.stdout.write(f"    邮箱: {student.contact_email}")
            if student.contact_phone:
                self.stdout.write(f"    电话: {student.contact_phone}")

        self.stdout.write('\n' + '相关数据统计:')
        self.stdout.write(f"  注册记录: {related_data['total_enrollments']} (活跃: {related_data['active_enrollments']})")
        self.stdout.write(f"  活动记录: {related_data['total_activities']} (最近30天: {related_data['recent_activities']})")
        self.stdout.write(f"  考勤记录: {related_data['total_attendances']} (最近30天: {related_data['recent_attendances']})")

    def perform_safety_checks(self, students, related_data):
        """执行安全检查"""
        warnings = []

        if related_data['active_enrollments'] > 0:
            warnings.append(f"存在 {related_data['active_enrollments']} 个活跃注册记录")

        if related_data['recent_activities'] > 0:
            warnings.append(f"最近30天内有 {related_data['recent_activities']} 个活动记录")

        if related_data['recent_attendances'] > 0:
            warnings.append(f"最近30天内有 {related_data['recent_attendances']} 个考勤记录")

        # 检查高价值学生
        high_activity_students = []
        for student in students:
            if student.activities.count() > 10:
                high_activity_students.append(student.get_full_name())

        if high_activity_students:
            warnings.append(f"以下学生拥有大量历史活动: {', '.join(high_activity_students)}")

        return warnings

    def show_warnings(self, warnings):
        """显示警告信息"""
        self.stdout.write('\n' + self.style.WARNING('安全警告:'))
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"⚠️  {warning}"))
        self.stdout.write('')

    def confirm_deletion(self, count, related_data):
        """确认删除操作"""
        total_records = (
            related_data['total_enrollments'] +
            related_data['total_activities'] +
            related_data['total_attendances']
        )

        self.stdout.write('')
        self.stdout.write(f"您即将删除 {count} 名学生及其相关的 {total_records} 条记录。")
        self.stdout.write(self.style.ERROR('此操作无法撤销！'))
        self.stdout.write('')

        response = input("请输入 'DELETE' 来确认删除操作: ")
        return response == 'DELETE'

    def delete_students(self, students, reason):
        """删除学生及相关数据"""
        deleted_count = 0
        summary = {
            'students': 0,
            'enrollments': 0,
            'activities': 0,
            'attendances': 0,
            'errors': []
        }

        for student in students:
            try:
                with transaction.atomic():
                    student_name = student.get_full_name()
                    student_id = student.id

                    # 统计将要删除的相关记录
                    enrollment_count = student.enrollments.count()
                    activity_count = student.activities.count()
                    attendance_count = student.attendances.count()

                    # 创建删除记录的活动日志
                    StudentActivity.create_activity(
                        student=student,
                        activity_type='other',
                        title='学生记录删除',
                        description=f'原因: {reason}. 删除的相关记录: {enrollment_count}个注册, {activity_count}个活动, {attendance_count}个考勤记录',
                        is_visible_to_student=False
                    )

                    # 删除学生 (CASCADE会处理相关记录)
                    student.delete()

                    deleted_count += 1
                    summary['students'] += 1
                    summary['enrollments'] += enrollment_count
                    summary['activities'] += activity_count + 1  # +1 for the deletion activity we just created
                    summary['attendances'] += attendance_count

                    self.stdout.write(
                        f"✓ 已删除学生: {student_name} (ID: {student_id}) "
                        f"及其 {enrollment_count} 个注册, {activity_count} 个活动, {attendance_count} 个考勤记录"
                    )

            except Exception as e:
                error_msg = f"删除学生 {student.get_full_name()} 时失败: {str(e)}"
                summary['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f"✗ {error_msg}"))

        return deleted_count, summary

    def show_deletion_summary(self, deleted_count, summary):
        """显示删除总结"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('删除操作完成'))
        self.stdout.write('=' * 60)

        self.stdout.write(f"成功删除的学生: {summary['students']}")
        self.stdout.write(f"删除的注册记录: {summary['enrollments']}")
        self.stdout.write(f"删除的活动记录: {summary['activities']}")
        self.stdout.write(f"删除的考勤记录: {summary['attendances']}")

        if summary['errors']:
            self.stdout.write(f"\n遇到的错误: {len(summary['errors'])}")
            for error in summary['errors']:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        self.stdout.write('\n删除操作已完成。')