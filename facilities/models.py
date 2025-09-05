from django.db import models


class Facility(models.Model):
    """
    Facility model - Educational facilities
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Facility Name'
    )
    address = models.TextField(
        verbose_name='Address'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Contact Phone'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    
    # GPS coordinates for teacher attendance verification
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Latitude',
        help_text='GPS latitude coordinate for attendance verification'
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Longitude',
        help_text='GPS longitude coordinate for attendance verification'
    )
    attendance_radius = models.PositiveIntegerField(
        default=50,
        verbose_name='Attendance Verification Radius (meters)',
        help_text='Maximum distance in meters for valid attendance check-in'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status'
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
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'
    
    def __str__(self):
        return self.name


class Classroom(models.Model):
    """
    Classroom model
    """
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name='Facility'
    )
    name = models.CharField(
        max_length=50,
        verbose_name='Classroom Name/Number'
    )
    capacity = models.PositiveIntegerField(
        verbose_name='Capacity'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active Status'
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
        verbose_name = 'Classroom'
        verbose_name_plural = 'Classrooms'
        unique_together = ['facility', 'name']
    
    def __str__(self):
        return f"{self.facility.name} - {self.name}"
