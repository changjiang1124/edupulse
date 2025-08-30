from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class Staff(AbstractUser):
    """
    员工模型 - 扩展Django内置用户模型
    包含教师和管理员角色
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
    ]
    
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Please enter a valid phone number')],
        verbose_name='Phone Number'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='teacher',
        verbose_name='Role'
    )
    is_active_staff = models.BooleanField(
        default=True,
        verbose_name='Staff Status'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
