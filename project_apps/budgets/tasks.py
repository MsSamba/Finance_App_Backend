from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import logging
import requests
from django.db import models
from django.core.mail import send_mail
from django.conf import settings

from .models import Budget, BudgetAlert, BudgetHistory

logger = logging.getLogger(__name__)

@shared_task
def check_budget_alerts(user_id=None):
    """Check and send budget alerts for users."""
    try:
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.filter(is_active=True)
        
        total_alerts = 0
        
        for user in users:
            user_alerts = check_user_budget_alerts(user)
            total_alerts += user_alerts
        
        logger.info(f"Processed budget alerts for {users.count()} users, sent {total_alerts} alerts")
        return f"Sent {total_alerts} budget alerts"
        
    except Exception as e:
        logger.error(f"Error in check_budget_alerts: {str(e)}")
        raise


def check_user_budget_alerts(user):
    """Check budget alerts for a specific user."""
    alerts_sent = 0
    
    # Get active budgets for user
    budgets = Budget.objects.filter(user=user, status='active')
    
    for budget in budgets:
        # Update spent amount first
        budget.update_spent_amount()
        
        # Check for threshold alert
        if budget.is_alert_threshold_reached and not budget.is_over_budget:
            alert_created = create_budget_alert(
                budget, 
                'threshold',
                f"Budget alert: You've reached {budget.percentage_used:.1f}% of your {budget.category} budget",
                budget.spent,
                budget.percentage_used
            )
            if alert_created:
                alerts_sent += 1
        
        # Check for exceeded alert
        if budget.is_over_budget:
            alert_created = create_budget_alert(
                budget,
                'exceeded',
                f"Budget exceeded: You've spent {budget.spent} out of {budget.limit} for {budget.category}",
                budget.spent,
                budget.percentage_used
            )
            if alert_created:
                alerts_sent += 1
        
        # Check for period ending alert (3 days before end)
        days_remaining = budget.days_remaining
        if days_remaining == 3:
            alert_created = create_budget_alert(
                budget,
                'period_ending',
                f"Budget period ending: Your {budget.category} budget period ends in 3 days",
                budget.spent,
                budget.percentage_used
            )
            if alert_created:
                alerts_sent += 1
        
        # Check for period ended alert
        if days_remaining == 0 and budget.is_current_period:
            alert_created = create_budget_alert(
                budget,
                'period_ended',
                f"Budget period ended: Your {budget.category} budget period has ended",
                budget.spent,
                budget.percentage_used
            )
            if alert_created:
                alerts_sent += 1
    
    return alerts_sent


def create_budget_alert(budget, alert_type, message, triggered_amount, triggered_percentage):
    """Create a budget alert if it doesn't already exist."""
    # Check if similar alert already exists and was sent recently
    existing_alert = BudgetAlert.objects.filter(
        budget=budget,
        alert_type=alert_type,
        triggered_amount=triggered_amount,
        created_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).first()
    
    if existing_alert:
        return False  # Alert already exists
    
    # Create new alert
    alert = BudgetAlert.objects.create(
        budget=budget,
        alert_type=alert_type,
        message=message,
        triggered_amount=triggered_amount,
        triggered_percentage=triggered_percentage
    )
    
    # Send notifications
    send_budget_notification(alert)
    
    return True


def send_budget_notification(alert):
    """Send budget notification via email and/or SMS."""
    budget = alert.budget
    user = budget.user
    
    email_sent = False
    sms_sent = False
    
    # Send email notification
    if budget.email_alerts and user.email:
        try:
            send_mail(
                subject=f"Budget Alert - {budget.category}",
                message=alert.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            email_sent = True
            logger.info(f"Email alert sent to {user.email} for budget {budget.category}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
    
    # Send SMS notification
    if budget.sms_alerts and hasattr(user, 'profile') and user.profile.phone_number:
        try:
            sms_sent = send_sms_alert(user.profile.phone_number, alert.message)
            if sms_sent:
                logger.info(f"SMS alert sent to {user.profile.phone_number} for budget {budget.category}")
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {str(e)}")
    
    # Mark alert as sent
    alert.mark_as_sent(email_sent=email_sent, sms_sent=sms_sent)


def send_sms_alert(phone_number, message):
    """Send SMS alert using configured SMS provider."""
    try:
        # Implement with SMS provider
        # Example with Twilio, Africa's Talking
        
        if not hasattr(settings, 'SMS_PROVIDER_API_KEY'):
            logger.warning("SMS provider not configured")
            return False
        
        # Example implementation (replace with your SMS provider)
        response = requests.post(
            settings.SMS_PROVIDER_URL,
            headers={
                'Authorization': f'Bearer {settings.SMS_PROVIDER_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'to': phone_number,
                'message': message
            },
            timeout=10
        )
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"SMS sending failed: {str(e)}")
        return False


@shared_task
def update_budget_spent_amounts():
    """Update spent amounts for all active budgets."""
    try:
        budgets = Budget.objects.filter(status='active')
        updated_count = 0
        
        for budget in budgets:
            old_spent = budget.spent
            budget.update_spent_amount()
            
            if budget.spent != old_spent:
                updated_count += 1
        
        logger.info(f"Updated spent amounts for {updated_count} budgets")
        return f"Updated {updated_count} budget spent amounts"
        
    except Exception as e:
        logger.error(f"Error updating budget spent amounts: {str(e)}")
        raise


@shared_task
def update_budget_history():
    """Create budget history records for completed periods."""
    try:
        today = timezone.now().date()
        
        # Find budgets with ended periods that don't have history records
        budgets_to_archive = Budget.objects.filter(
            period_end__lt=today,
            status='active'
        ).exclude(
            history__period_end=models.F('period_end')
        )
        
        archived_count = 0
        
        for budget in budgets_to_archive:
            # Create history record
            BudgetHistory.objects.create(
                budget=budget,
                period_start=budget.period_start,
                period_end=budget.period_end,
                limit=budget.limit,
                spent=budget.spent,
                percentage_used=budget.percentage_used,
                was_exceeded=budget.is_over_budget
            )
            
            # Update budget for next period
            budget.period_start = budget.period_end + timezone.timedelta(days=1)
            budget.period_end = budget.calculate_period_end()
            budget.spent = Decimal('0.00')
            budget.save()
            
            archived_count += 1
        
        logger.info(f"Archived {archived_count} budget periods")
        return f"Archived {archived_count} budget periods"
        
    except Exception as e:
        logger.error(f"Error updating budget history: {str(e)}")
        raise


@shared_task
def cleanup_old_alerts():
    """Clean up old budget alerts (older than 90 days)."""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=90)
        
        deleted_count, _ = BudgetAlert.objects.filter(
            created_at__lt=cutoff_date,
            is_sent=True
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old budget alerts")
        return f"Cleaned up {deleted_count} old alerts"
        
    except Exception as e:
        logger.error(f"Error cleaning up old alerts: {str(e)}")
        raise


@shared_task
def generate_budget_reports():
    """Generate monthly budget reports for users."""
    try:
        # This is a placeholder for generating monthly reports
        # You can implement PDF generation, email reports, etc.
        
        users_with_budgets = User.objects.filter(
            budgets__isnull=False,
            is_active=True
        ).distinct()
        
        reports_generated = 0
        
        for user in users_with_budgets:
            # Generate report logic here
            # For now, just log
            logger.info(f"Would generate budget report for {user.username}")
            reports_generated += 1
        
        return f"Generated {reports_generated} budget reports"
        
    except Exception as e:
        logger.error(f"Error generating budget reports: {str(e)}")
        raise


@shared_task
def create_budget_alert(budget_id):
    """Create a specific budget alert"""
    try:
        budget = Budget.objects.get(id=budget_id)
        
        if budget.is_over_budget:
            alert_type = 'exceeded'
            message = f'Your {budget.category} budget has been exceeded by KES {budget.spent - budget.limit:.2f}.'
        elif budget.is_alert_threshold_reached:
            alert_type = 'threshold'
            message = f'Your {budget.category} budget has reached {budget.percentage_used:.1f}% of the limit.'
        else:
            return "No alert needed"
        
        # Check if similar alert exists recently
        recent_alert = BudgetAlert.objects.filter(
            budget=budget,
            alert_type=alert_type,
            created_at__gte=timezone.now() - timezone.timedelta(hours=6)
        ).exists()
        
        if not recent_alert:
            alert = BudgetAlert.objects.create(
                budget=budget,
                alert_type=alert_type,
                message=message
            )
            
            # Send email/SMS if enabled
            if budget.email_alerts:
                send_email_alert.delay(alert.id)
            if budget.sms_alerts:
                send_sms_alert.delay(alert.id)
            
            return f"Alert created for {budget.category}"
        
        return "Recent alert already exists"
        
    except Budget.DoesNotExist:
        return "Budget not found"


@shared_task
def send_email_alert(alert_id):
    """Send email alert to user"""
    try:
        alert = BudgetAlert.objects.get(id=alert_id)
        
        # TODO: Implement email sending logic
        # For now, just mark as sent
        alert.email_sent = True
        alert.save(update_fields=['email_sent'])
        
        return f"Email sent for alert {alert_id}"
        
    except BudgetAlert.DoesNotExist:
        return "Alert not found"


@shared_task
def send_sms_alert(alert_id):
    """Send SMS alert to user"""
    try:
        alert = BudgetAlert.objects.get(id=alert_id)
        
        # TODO: Implement SMS sending logic
        # For now, just mark as sent
        alert.sms_sent = True
        alert.save(update_fields=['sms_sent'])
        
        return f"SMS sent for alert {alert_id}"
        
    except BudgetAlert.DoesNotExist:
        return "Alert not found"


@shared_task
def archive_budget_history():
    """Archive completed budget periods to history"""
    now = timezone.now()
    budgets_to_archive = Budget.objects.filter(
        period_end__lt=now,
        status='active'
    )
    
    archived_count = 0
    
    for budget in budgets_to_archive:
        # Create history entry
        BudgetHistory.objects.create(
            budget=budget,
            period_start=budget.period_start,
            period_end=budget.period_end,
            limit=budget.limit,
            spent=budget.spent,
            performance_score=budget.performance_score
        )
        
        # Advance budget to next period
        budget.advance_period()
        archived_count += 1
    
    return f"Archived {archived_count} budget periods"


@shared_task
def cleanup_old_alerts():
    """Clean up old read alerts"""
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    deleted_count = BudgetAlert.objects.filter(
        is_read=True,
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Deleted {deleted_count} old alerts"
