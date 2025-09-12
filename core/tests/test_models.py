from django.test import TestCase
from django.utils import timezone
from datetime import date
from core.models import NotificationQuota


class NotificationQuotaModelTest(TestCase):
    """Test cases for NotificationQuota model"""
    
    def setUp(self):
        """Set up test data"""
        self.current_year = timezone.now().year
        self.current_month = timezone.now().month
        
        # Create test quotas
        self.email_quota = NotificationQuota.objects.create(
            notification_type='email',
            year=self.current_year,
            month=self.current_month,
            monthly_limit=100,
            used_count=30
        )
        
        self.sms_quota = NotificationQuota.objects.create(
            notification_type='sms',
            year=self.current_year,
            month=self.current_month,
            monthly_limit=50,
            used_count=45
        )
    
    def test_quota_creation(self):
        """Test quota object creation"""
        self.assertEqual(self.email_quota.notification_type, 'email')
        self.assertEqual(self.email_quota.monthly_limit, 100)
        self.assertEqual(self.email_quota.used_count, 30)
    
    def test_remaining_quota_property(self):
        """Test remaining quota calculation"""
        self.assertEqual(self.email_quota.remaining_quota, 70)
        self.assertEqual(self.sms_quota.remaining_quota, 5)
    
    def test_usage_percentage_property(self):
        """Test usage percentage calculation"""
        self.assertEqual(self.email_quota.usage_percentage, 30.0)  # 30/100 * 100
        self.assertEqual(self.sms_quota.usage_percentage, 90.0)    # 45/50 * 100
    
    def test_is_quota_exceeded_property(self):
        """Test quota exceeded check"""
        self.assertFalse(self.email_quota.is_quota_exceeded)
        self.assertFalse(self.sms_quota.is_quota_exceeded)  # 45 < 50
        
        # Test exceeded scenario
        self.sms_quota.used_count = 50
        self.sms_quota.save()
        self.assertTrue(self.sms_quota.is_quota_exceeded)
    
    def test_get_current_quota_existing(self):
        """Test getting existing current quota"""
        quota = NotificationQuota.get_current_quota('email')
        self.assertEqual(quota.pk, self.email_quota.pk)
        self.assertEqual(quota.used_count, 30)
    
    def test_get_current_quota_new(self):
        """Test creating new quota when none exists"""
        # Delete existing quota
        NotificationQuota.objects.filter(notification_type='email').delete()
        
        quota = NotificationQuota.get_current_quota('email')
        self.assertEqual(quota.notification_type, 'email')
        self.assertEqual(quota.monthly_limit, 200)  # Default limit
        self.assertEqual(quota.used_count, 0)
        self.assertEqual(quota.year, self.current_year)
        self.assertEqual(quota.month, self.current_month)
    
    def test_check_quota_available(self):
        """Test quota availability check"""
        self.assertTrue(NotificationQuota.check_quota_available('email', 50))
        self.assertTrue(NotificationQuota.check_quota_available('email', 70))
        self.assertFalse(NotificationQuota.check_quota_available('email', 80))
        
        self.assertTrue(NotificationQuota.check_quota_available('sms', 5))
        self.assertFalse(NotificationQuota.check_quota_available('sms', 10))
    
    def test_consume_quota(self):
        """Test quota consumption"""
        initial_used = self.email_quota.used_count
        
        updated_quota = NotificationQuota.consume_quota('email', 10)
        self.assertEqual(updated_quota.used_count, initial_used + 10)
        
        # Verify database was updated
        self.email_quota.refresh_from_db()
        self.assertEqual(self.email_quota.used_count, initial_used + 10)
    
    def test_unique_constraint(self):
        """Test unique constraint on notification_type, year, month"""
        with self.assertRaises(Exception):
            NotificationQuota.objects.create(
                notification_type='email',
                year=self.current_year,
                month=self.current_month,
                monthly_limit=200
            )
    
    def test_str_representation(self):
        """Test string representation"""
        expected = f'Email {self.current_year}-{self.current_month:02d}: 30/100'
        self.assertEqual(str(self.email_quota), expected)
    
    def test_usage_percentage_with_zero_limit(self):
        """Test usage percentage when limit is zero"""
        zero_quota = NotificationQuota.objects.create(
            notification_type='email',
            year=2024,
            month=1,
            monthly_limit=0,
            used_count=5
        )
        self.assertEqual(zero_quota.usage_percentage, 100)
    
    def test_remaining_quota_negative_handling(self):
        """Test remaining quota when usage exceeds limit"""
        over_quota = NotificationQuota.objects.create(
            notification_type='sms',
            year=2024,
            month=1,
            monthly_limit=10,
            used_count=15
        )
        self.assertEqual(over_quota.remaining_quota, 0)  # Should not be negative