from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect


class ActiveStaffRequiredMixin(UserPassesTestMixin):
    """Restrict access to active staff accounts with allowed roles."""

    allowed_roles = ()

    def expects_json(self):
        content_type = self.request.content_type or ''
        accept = self.request.headers.get('Accept', '')
        requested_with = self.request.headers.get('X-Requested-With', '')

        return (
            'application/json' in content_type or
            'application/json' in accept or
            requested_with == 'XMLHttpRequest'
        )

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        if getattr(user, 'is_superuser', False):
            return True

        if not getattr(user, 'is_active_staff', True):
            return False

        if not self.allowed_roles:
            return True

        return getattr(user, 'role', None) in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            if self.expects_json():
                return JsonResponse({
                    'success': False,
                    'error': 'Access denied. Please log in.',
                    'message': 'Access denied. Please log in.'
                }, status=403)
            return super().handle_no_permission()

        if self.expects_json():
            return JsonResponse({
                'success': False,
                'error': 'Access denied.',
                'message': 'Access denied.'
            }, status=403)

        messages.error(self.request, 'Access denied.')
        return redirect('dashboard')


class AdminRequiredMixin(ActiveStaffRequiredMixin):
    """Admin permission check mixin."""

    allowed_roles = ('admin',)


class TeacherOrAdminRequiredMixin(ActiveStaffRequiredMixin):
    """Teacher/admin permission check mixin."""

    allowed_roles = ('teacher', 'admin')
