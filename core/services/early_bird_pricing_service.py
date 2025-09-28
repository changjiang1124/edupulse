"""
Early Bird Pricing Service for EduPulse
Handles early bird pricing validation and adjustment logic
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class EarlyBirdPricingService:
    """
    Service class to handle early bird pricing validation and adjustments
    """

    @staticmethod
    def check_price_adjustment_needed(enrollment, current_action_date=None):
        """
        Check if enrollment pricing needs adjustment based on early bird deadline

        Args:
            enrollment: Enrollment instance
            current_action_date: Date of current action (defaults to today)

        Returns:
            dict: {
                'needs_adjustment': bool,
                'reason': str,
                'enrollment_date': date,
                'early_bird_deadline': date,
                'action_date': date,
                'current_price': Decimal,
                'suggested_price': Decimal,
                'price_difference': Decimal,
                'was_early_bird': bool,
                'should_be_early_bird': bool
            }
        """
        try:
            course = enrollment.course
            current_date = current_action_date or timezone.now().date()
            enrollment_date = enrollment.created_at.date()

            # Initialize result
            result = {
                'needs_adjustment': False,
                'reason': '',
                'enrollment_date': enrollment_date,
                'early_bird_deadline': course.early_bird_deadline,
                'action_date': current_date,
                'current_price': enrollment.course_fee or Decimal('0'),
                'suggested_price': enrollment.course_fee or Decimal('0'),
                'price_difference': Decimal('0'),
                'was_early_bird': enrollment.is_early_bird,
                'should_be_early_bird': False
            }

            # Skip if course has no early bird pricing
            if not course.has_early_bird_pricing():
                result['reason'] = 'Course has no early bird pricing configured'
                return result

            # Determine if enrollment should be early bird based on action date
            should_be_early_bird = course.is_early_bird_available(current_date)
            was_early_bird_at_enrollment = course.is_early_bird_available(enrollment_date)

            result['should_be_early_bird'] = should_be_early_bird

            # Calculate suggested price based on current action date
            suggested_price = course.get_applicable_price(current_date)
            result['suggested_price'] = suggested_price
            current_price = enrollment.course_fee or Decimal('0')
            result['price_difference'] = current_price - suggested_price

            # Case 1: Enrolled during early bird period, but acting after deadline
            if (was_early_bird_at_enrollment and enrollment.is_early_bird and
                not should_be_early_bird and current_price != suggested_price):
                result['needs_adjustment'] = True
                result['reason'] = (
                    f'Student enrolled during early bird period ({enrollment_date}), '
                    f'but action is being taken after early bird deadline ({course.early_bird_deadline}). '
                    f'Consider adjusting price from ${current_price} to ${suggested_price} (regular price).'
                )

            # Case 2: Enrolled with early bird pricing but deadline has passed
            elif (enrollment.is_early_bird and not should_be_early_bird and
                  current_price != suggested_price):
                result['needs_adjustment'] = True
                result['reason'] = (
                    f'Enrollment has early bird pricing (${current_price}) '
                    f'but early bird deadline ({course.early_bird_deadline}) has passed. '
                    f'Consider adjusting to regular price (${suggested_price}).'
                )

            # Case 3: Price mismatch - enrollment price doesn't match what it should be
            elif current_price != suggested_price:
                result['needs_adjustment'] = True
                price_type = 'early bird' if should_be_early_bird else 'regular'
                result['reason'] = (
                    f'Current enrollment price (${current_price}) '
                    f'does not match expected {price_type} price (${suggested_price}) '
                    f'for action date {current_date}.'
                )

            return result

        except Exception as e:
            logger.error(f"Error checking price adjustment for enrollment {enrollment.id}: {str(e)}")
            return {
                'needs_adjustment': False,
                'reason': f'Error checking pricing: {str(e)}',
                'enrollment_date': None,
                'early_bird_deadline': None,
                'action_date': current_action_date or timezone.now().date(),
                'current_price': enrollment.course_fee or Decimal('0'),
                'suggested_price': enrollment.course_fee or Decimal('0'),
                'price_difference': Decimal('0'),
                'was_early_bird': enrollment.is_early_bird,
                'should_be_early_bird': False
            }

    @staticmethod
    def apply_price_adjustment(enrollment, use_regular_price=True, performed_by=None):
        """
        Apply price adjustment to enrollment

        Args:
            enrollment: Enrollment instance
            use_regular_price: If True, apply regular price; if False, keep early bird price
            performed_by: Staff user performing the adjustment

        Returns:
            dict: {
                'success': bool,
                'previous_price': Decimal,
                'new_price': Decimal,
                'price_difference': Decimal,
                'adjustment_type': str,
                'message': str
            }
        """
        try:
            course = enrollment.course
            previous_price = enrollment.course_fee
            previous_early_bird_status = enrollment.is_early_bird

            # Calculate new pricing
            if use_regular_price:
                # Apply regular pricing
                new_price = course.price
                enrollment.course_fee = new_price
                enrollment.is_early_bird = False
                enrollment.original_price = None
                enrollment.early_bird_savings = None
                adjustment_type = 'regular_price_applied'
                message = f'Price adjusted to regular price: ${new_price}'
            else:
                # Keep early bird pricing
                new_price = course.early_bird_price or course.price
                enrollment.course_fee = new_price
                enrollment.is_early_bird = True
                enrollment.original_price = course.price
                enrollment.early_bird_savings = course.get_early_bird_savings()
                adjustment_type = 'early_bird_price_maintained'
                message = f'Early bird price maintained: ${new_price}'

            # Update form_data to record the adjustment decision
            if not enrollment.form_data:
                enrollment.form_data = {}

            enrollment.form_data.update({
                'price_adjustment_performed': True,
                'price_adjustment_date': timezone.now().isoformat(),
                'price_adjustment_type': adjustment_type,
                'previous_price': str(previous_price),
                'new_price': str(new_price),
                'performed_by': performed_by.username if performed_by else 'system',
                'previous_early_bird_status': previous_early_bird_status
            })

            enrollment.save()

            # Create audit log entry
            EarlyBirdPricingService._create_price_adjustment_activity(
                enrollment,
                previous_price,
                new_price,
                adjustment_type,
                performed_by
            )

            return {
                'success': True,
                'previous_price': previous_price,
                'new_price': new_price,
                'price_difference': previous_price - new_price,
                'adjustment_type': adjustment_type,
                'message': message
            }

        except Exception as e:
            logger.error(f"Error applying price adjustment to enrollment {enrollment.id}: {str(e)}")
            return {
                'success': False,
                'previous_price': enrollment.course_fee,
                'new_price': enrollment.course_fee,
                'price_difference': Decimal('0'),
                'adjustment_type': 'error',
                'message': f'Error applying price adjustment: {str(e)}'
            }

    @staticmethod
    def _create_price_adjustment_activity(enrollment, previous_price, new_price, adjustment_type, performed_by):
        """Create student activity record for price adjustment"""
        try:
            from students.models import StudentActivity

            # Determine description based on adjustment type
            if adjustment_type == 'regular_price_applied':
                description = (
                    f'Price adjusted from early bird ${previous_price} to regular price ${new_price} '
                    f'due to early bird deadline expiry. Staff decision: apply regular pricing.'
                )
            elif adjustment_type == 'early_bird_price_maintained':
                description = (
                    f'Early bird price ${new_price} maintained despite deadline expiry. '
                    f'Staff decision: honor early bird pricing from enrollment date.'
                )
            else:
                description = (
                    f'Price adjusted from ${previous_price} to ${new_price}. '
                    f'Adjustment type: {adjustment_type}'
                )

            StudentActivity.create_activity(
                student=enrollment.student,
                activity_type='price_adjustment',
                title=f'Course fee adjusted for {enrollment.course.name}',
                description=description,
                enrollment=enrollment,
                course=enrollment.course,
                performed_by=performed_by,
                metadata={
                    'adjustment_type': adjustment_type,
                    'previous_price': str(previous_price),
                    'new_price': str(new_price),
                    'price_difference': str(previous_price - new_price),
                    'early_bird_deadline': enrollment.course.early_bird_deadline.isoformat() if enrollment.course.early_bird_deadline else None,
                    'adjustment_reason': 'early_bird_deadline_check'
                }
            )

        except Exception as e:
            logger.error(f"Error creating price adjustment activity: {str(e)}")

    @staticmethod
    def get_price_adjustment_summary(enrollment, current_action_date=None):
        """
        Get a comprehensive summary for price adjustment decision

        Args:
            enrollment: Enrollment instance
            current_action_date: Date of current action

        Returns:
            dict: Summary information for frontend display
        """
        check_result = EarlyBirdPricingService.check_price_adjustment_needed(
            enrollment, current_action_date
        )

        course = enrollment.course

        summary = {
            'needs_adjustment': check_result['needs_adjustment'],
            'reason': check_result['reason'],
            'enrollment_date': check_result['enrollment_date'],
            'early_bird_deadline': check_result['early_bird_deadline'],
            'action_date': check_result['action_date'],

            # Current enrollment pricing
            'current_enrollment_price': enrollment.course_fee,
            'current_is_early_bird': enrollment.is_early_bird,
            'current_savings': enrollment.early_bird_savings or Decimal('0'),

            # Course pricing options
            'course_regular_price': course.price,
            'course_early_bird_price': course.early_bird_price,
            'course_early_bird_savings': course.get_early_bird_savings() if course.has_early_bird_pricing() else Decimal('0'),

            # Suggested pricing
            'suggested_price': check_result['suggested_price'],
            'price_difference': check_result['price_difference'],

            # Decision options
            'option_keep_early_bird': {
                'price': course.early_bird_price or course.price,
                'savings': course.get_early_bird_savings() if course.has_early_bird_pricing() else Decimal('0'),
                'description': 'Honor early bird pricing from enrollment date'
            },
            'option_apply_regular': {
                'price': course.price,
                'savings': Decimal('0'),
                'description': 'Apply current regular pricing'
            }
        }

        return summary