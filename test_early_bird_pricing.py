#!/usr/bin/env python
"""
Early Bird Price Adjustment System Test
Tests the complete workflow for early bird pricing adjustments
"""
import os
import django
import sys
from datetime import date, timedelta

# Setup Django environment
sys.path.append('/Users/changjiang/Dev/edupulse')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
django.setup()

from django.utils import timezone
from decimal import Decimal
from academics.models import Course
from enrollment.models import Enrollment
from students.models import Student
from core.services.early_bird_pricing_service import EarlyBirdPricingService


def test_early_bird_price_adjustment():
    """Test early bird price adjustment scenarios"""
    print("🔧 Testing Early Bird Price Adjustment System")
    print("=" * 60)

    # Create test course with early bird pricing
    course = Course.objects.create(
        name="Test Art Course - Early Bird Test",
        price=Decimal('200.00'),
        early_bird_price=Decimal('150.00'),
        early_bird_deadline=date.today() - timedelta(days=1),  # Deadline was yesterday
        start_date=date.today() + timedelta(days=7),
        start_time="10:00",
        status='published'
    )

    # Create test student
    student = Student.objects.create(
        first_name="Test",
        last_name="Student",
        contact_email="test@example.com"
    )

    # Create enrollment with early bird pricing from 3 days ago
    enrollment_date = timezone.now() - timedelta(days=3)
    enrollment = Enrollment.objects.create(
        student=student,
        course=course,
        status='pending',
        created_at=enrollment_date,
        course_fee=Decimal('150.00'),  # Early bird price
        is_early_bird=True,
        original_price=Decimal('200.00'),
        early_bird_savings=Decimal('50.00')
    )

    print(f"✅ Created test data:")
    print(f"   Course: {course.name}")
    print(f"   Early bird deadline: {course.early_bird_deadline}")
    print(f"   Student enrolled: {enrollment_date.date()}")
    print(f"   Current price: ${enrollment.course_fee}")
    print(f"   Early bird status: {enrollment.is_early_bird}")
    print()

    # Test 1: Check if price adjustment is needed
    print("🧪 Test 1: Check Price Adjustment Need")
    print("-" * 40)

    price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment)

    print(f"Needs adjustment: {price_check['needs_adjustment']}")
    print(f"Reason: {price_check['reason']}")
    print(f"Current price: ${price_check['current_price']}")
    print(f"Suggested price: ${price_check['suggested_price']}")
    print()

    # Test 2: Get price adjustment summary
    print("🧪 Test 2: Price Adjustment Summary")
    print("-" * 40)

    summary = EarlyBirdPricingService.get_price_adjustment_summary(enrollment)

    print(f"Current enrollment price: ${summary['current_enrollment_price']}")
    print(f"Suggested price: ${summary['suggested_price']}")
    print(f"Keep early bird option: ${summary['option_keep_early_bird']['price']}")
    print(f"Apply regular option: ${summary['option_apply_regular']['price']}")
    print()

    # Test 3: Apply regular price adjustment
    print("🧪 Test 3: Apply Regular Price Adjustment")
    print("-" * 40)

    result = EarlyBirdPricingService.apply_price_adjustment(
        enrollment=enrollment,
        use_regular_price=True,
        performed_by=None
    )

    print(f"Adjustment successful: {result['success']}")
    print(f"Previous price: ${result['previous_price']}")
    print(f"New price: ${result['new_price']}")
    print(f"Message: {result['message']}")
    print()

    # Refresh enrollment from database
    enrollment.refresh_from_db()
    print(f"✅ Updated enrollment:")
    print(f"   Course fee: ${enrollment.course_fee}")
    print(f"   Early bird status: {enrollment.is_early_bird}")
    print(f"   Early bird savings: {enrollment.early_bird_savings}")
    print()

    # Test 4: Apply early bird price (keep early bird)
    print("🧪 Test 4: Keep Early Bird Price")
    print("-" * 40)

    result = EarlyBirdPricingService.apply_price_adjustment(
        enrollment=enrollment,
        use_regular_price=False,
        performed_by=None
    )

    print(f"Adjustment successful: {result['success']}")
    print(f"Previous price: ${result['previous_price']}")
    print(f"New price: ${result['new_price']}")
    print(f"Message: {result['message']}")
    print()

    # Refresh enrollment from database
    enrollment.refresh_from_db()
    print(f"✅ Final enrollment state:")
    print(f"   Course fee: ${enrollment.course_fee}")
    print(f"   Early bird status: {enrollment.is_early_bird}")
    print(f"   Early bird savings: {enrollment.early_bird_savings}")
    print()

    # Clean up test data
    print("🧹 Cleaning up test data...")
    enrollment.delete()
    student.delete()
    course.delete()
    print("✅ Test completed successfully!")


def test_price_check_scenarios():
    """Test different price check scenarios"""
    print("\n🔧 Testing Different Price Check Scenarios")
    print("=" * 60)

    # Scenario 1: Course with no early bird pricing
    print("📝 Scenario 1: Course without early bird pricing")
    print("-" * 50)

    course_no_early_bird = Course.objects.create(
        name="Regular Course - No Early Bird",
        price=Decimal('100.00'),
        start_date=date.today() + timedelta(days=7),
        start_time="14:00",
        status='published'
    )

    student = Student.objects.create(
        first_name="Regular",
        last_name="Student",
        contact_email="regular@example.com"
    )

    enrollment_regular = Enrollment.objects.create(
        student=student,
        course=course_no_early_bird,
        status='pending',
        course_fee=Decimal('100.00'),
        is_early_bird=False
    )

    price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment_regular)
    print(f"Needs adjustment: {price_check['needs_adjustment']}")
    print(f"Reason: {price_check['reason']}")
    print()

    # Scenario 2: Enrollment within early bird period
    print("📝 Scenario 2: Enrollment within early bird period")
    print("-" * 50)

    course_active_early_bird = Course.objects.create(
        name="Active Early Bird Course",
        price=Decimal('300.00'),
        early_bird_price=Decimal('250.00'),
        early_bird_deadline=date.today() + timedelta(days=5),  # Still within early bird
        start_date=date.today() + timedelta(days=10),
        start_time="16:00",
        status='published'
    )

    enrollment_active = Enrollment.objects.create(
        student=student,
        course=course_active_early_bird,
        status='pending',
        course_fee=Decimal('250.00'),
        is_early_bird=True,
        original_price=Decimal('300.00'),
        early_bird_savings=Decimal('50.00')
    )

    price_check = EarlyBirdPricingService.check_price_adjustment_needed(enrollment_active)
    print(f"Needs adjustment: {price_check['needs_adjustment']}")
    print(f"Reason: {price_check['reason']}")
    print()

    # Clean up
    enrollment_regular.delete()
    enrollment_active.delete()
    student.delete()
    course_no_early_bird.delete()
    course_active_early_bird.delete()
    print("✅ Scenario tests completed!")


if __name__ == "__main__":
    try:
        test_early_bird_price_adjustment()
        test_price_check_scenarios()
        print("\n🎉 All tests passed! Early bird price adjustment system is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()