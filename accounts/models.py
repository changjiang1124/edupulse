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
        blank=True,
        validators=[RegexValidator(
            r'^(0[4-5]\d{2}\s?\d{3}\s?\d{3}|0[2,3,7-9]\d?\s?\d{4}\s?\d{4}|0[2,3,7-9]\d{8})$', 
            'Please enter a valid Australian phone number (e.g., 0412 345 678, 02 1234 5678)'
        )],
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
