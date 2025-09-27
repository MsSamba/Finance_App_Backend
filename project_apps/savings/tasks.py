from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from django.db import models

from .models import (
    SavingsAccount, SavingsGoal, SavingsTransaction, 
    SavingsReport, SavingsSettings
)

logger = logging.getLogger(__name__)


@shared_task
def generate_monthly_savings_report(user_id, report_date=None):
    """
    Generate monthly savings report for a user
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        if not report_date:
            report_date = timezone.now().date().replace(day=1)
        else:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        
        # Calculate period
        period_start = report_date
        if report_date.month == 12:
            period_end = report_date.replace(year=report_date.year + 1, month=1) - timedelta(days=1)
        else:
            period_end = report_date.replace(month=report_date.month + 1) - timedelta(days=1)
        
        # Get savings account
        try:
            savings_account = SavingsAccount.objects.get(user=user)
        except SavingsAccount.DoesNotExist:
            logger.warning(f"No savings account found for user {user.username}")
            return
        
        # Calculate savings data
        transactions = SavingsTransaction.objects.filter(
            savings_account=savings_account,
            created_at__date__range=[period_start, period_end]
        )
        
        total_saved = transactions.filter(
            transaction_type__in=['deposit', 'auto_save']
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        auto_saved = transactions.filter(
            transaction_type='auto_save'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        manual_saved = total_saved - auto_saved
        
        total_withdrawn = transactions.filter(
            transaction_type='withdrawal'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        net_savings = total_saved - total_withdrawn
        
        # Calculate goals data
        goals = SavingsGoal.objects.filter(user=user)
        goals_completed = goals.filter(
            status='completed',
            completed_at__date__range=[period_start, period_end]
        ).count()
        
        goals_in_progress = goals.filter(status='active').count()
        
        # Calculate average progress
        active_goals = goals.filter(status='active')
        if active_goals.exists():
            total_progress = sum(goal.progress_percentage for goal in active_goals)
            average_goal_progress = Decimal(str(total_progress / active_goals.count()))
        else:
            average_goal_progress = Decimal('0.00')
        
        # Create or update report
        report, created = SavingsReport.objects.update_or_create(
            user=user,
            report_date=report_date,
            defaults={
                'period_start': period_start,
                'period_end': period_end,
                'total_saved': total_saved,
                'auto_saved': auto_saved,
                'manual_saved': manual_saved,
                'total_withdrawn': total_withdrawn,
                'net_savings': net_savings,
                'goals_completed': goals_completed,
                'goals_in_progress': goals_in_progress,
                'average_goal_progress': average_goal_progress,
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} savings report for {user.username} - {report_date}")
        
        return {
            'user_id': user_id,
            'report_date': report_date.isoformat(),
            'total_saved': float(total_saved),
            'net_savings': float(net_savings),
            'goals_completed': goals_completed,
            'action': action.lower()
        }
        
    except Exception as e:
        logger.error(f"Error generating savings report for user {user_id}: {str(e)}")
        raise


@shared_task
def check_savings_goal_deadlines():
    """
    Check for savings goals approaching their target dates
    """
    try:
        today = timezone.now().date()
        warning_date = today + timedelta(days=30)  # 30 days warning
        
        # Get goals approaching deadline
        approaching_goals = SavingsGoal.objects.filter(
            status='active',
            target_date__lte=warning_date,
            target_date__gte=today
        ).select_related('user')
        
        notifications_sent = 0
        
        for goal in approaching_goals:
            # Check if user wants notifications
            try:
                settings = SavingsSettings.objects.get(user=goal.user)
                if not settings.goal_reminders:
                    continue
            except SavingsSettings.DoesNotExist:
                continue
            
            days_remaining = (goal.target_date - today).days
            progress = goal.progress_percentage
            
            # Send notification based on urgency
            if days_remaining <= 7 and progress < 90:
                # Critical: Less than a week and not close to completion
                send_goal_deadline_notification.delay(
                    goal.id, 'critical', days_remaining
                )
                notifications_sent += 1
            elif days_remaining <= 14 and progress < 75:
                # Warning: Less than 2 weeks and not on track
                send_goal_deadline_notification.delay(
                    goal.id, 'warning', days_remaining
                )
                notifications_sent += 1
            elif days_remaining <= 30 and progress < 50:
                # Info: Less than a month and behind schedule
                send_goal_deadline_notification.delay(
                    goal.id, 'info', days_remaining
                )
                notifications_sent += 1
        
        logger.info(f"Checked {approaching_goals.count()} goals, sent {notifications_sent} notifications")
        
        return {
            'goals_checked': approaching_goals.count(),
            'notifications_sent': notifications_sent
        }
        
    except Exception as e:
        logger.error(f"Error checking savings goal deadlines: {str(e)}")
        raise


@shared_task
def send_goal_deadline_notification(goal_id, urgency, days_remaining):
    """
    Send notification about approaching goal deadline
    """
    try:
        goal = SavingsGoal.objects.get(id=goal_id)
        
        # Create notification message
        if urgency == 'critical':
            message = f"🚨 Critical: Your savings goal '{goal.name}' is due in {days_remaining} days and you're at {goal.progress_percentage:.1f}% completion!"
        elif urgency == 'warning':
            message = f"⚠️ Warning: Your savings goal '{goal.name}' is due in {days_remaining} days. You're at {goal.progress_percentage:.1f}% - consider increasing your contributions."
        else:
            message = f"📅 Reminder: Your savings goal '{goal.name}' is due in {days_remaining} days. Current progress: {goal.progress_percentage:.1f}%"
        
        # Here you would integrate with your notification system
        # For example: send email, push notification, SMS, etc.
        logger.info(f"Notification sent for goal {goal.name}: {message}")
        
        return {
            'goal_id': str(goal_id),
            'goal_name': goal.name,
            'urgency': urgency,
            'days_remaining': days_remaining,
            'message': message
        }
        
    except SavingsGoal.DoesNotExist:
        logger.error(f"Savings goal {goal_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error sending goal deadline notification: {str(e)}")
        raise


@shared_task
def auto_complete_achieved_goals():
    """
    Automatically mark goals as completed when they reach their target
    """
    try:
        # Find goals that have reached their target but aren't marked as completed
        achieved_goals = SavingsGoal.objects.filter(
            status='active',
            current_amount__gte=models.F('target_amount')
        )
        
        completed_count = 0
        
        for goal in achieved_goals:
            goal.status = 'completed'
            goal.completed_at = timezone.now()
            goal.save(update_fields=['status', 'completed_at', 'updated_at'])
            
            # Send congratulations notification
            send_goal_completion_notification.delay(goal.id)
            completed_count += 1
        
        logger.info(f"Auto-completed {completed_count} achieved goals")
        
        return {
            'goals_completed': completed_count
        }
        
    except Exception as e:
        logger.error(f"Error auto-completing achieved goals: {str(e)}")
        raise


@shared_task
def send_goal_completion_notification(goal_id):
    """
    Send congratulations notification for completed goal
    """
    try:
        goal = SavingsGoal.objects.get(id=goal_id)
        
        message = f"🎉 Congratulations! You've successfully completed your savings goal '{goal.name}' with {goal.current_amount} saved!"
        
        # Here you would integrate with your notification system
        logger.info(f"Completion notification sent for goal {goal.name}")
        
        return {
            'goal_id': str(goal_id),
            'goal_name': goal.name,
            'amount_saved': float(goal.current_amount),
            'message': message
        }
        
    except SavingsGoal.DoesNotExist:
        logger.error(f"Savings goal {goal_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error sending goal completion notification: {str(e)}")
        raise


@shared_task
def cleanup_old_savings_data():
    """
    Clean up old savings data (reports, transactions, etc.)
    """
    try:
        cutoff_date = timezone.now().date() - timedelta(days=365 * 2)  # 2 years ago
        
        # Clean up old reports (keep last 2 years)
        old_reports = SavingsReport.objects.filter(report_date__lt=cutoff_date)
        reports_deleted = old_reports.count()
        old_reports.delete()
        
        # Clean up old transactions (keep last 2 years)
        old_transactions = SavingsTransaction.objects.filter(created_at__date__lt=cutoff_date)
        transactions_deleted = old_transactions.count()
        old_transactions.delete()
        
        logger.info(f"Cleaned up {reports_deleted} old reports and {transactions_deleted} old transactions")
        
        return {
            'reports_deleted': reports_deleted,
            'transactions_deleted': transactions_deleted,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old savings data: {str(e)}")
        raise


@shared_task
def generate_savings_insights(user_id):
    """
    Generate personalized savings insights for a user
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get user's savings data
        try:
            savings_account = SavingsAccount.objects.get(user=user)
        except SavingsAccount.DoesNotExist:
            return {'error': 'No savings account found'}
        
        goals = SavingsGoal.objects.filter(user=user)
        
        # Calculate insights
        insights = []
        
        # Savings rate insight
        last_30_days = timezone.now().date() - timedelta(days=30)
        recent_savings = SavingsTransaction.objects.filter(
            savings_account=savings_account,
            transaction_type__in=['deposit', 'auto_save'],
            created_at__date__gte=last_30_days
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        
        if recent_savings > 0:
            insights.append({
                'type': 'savings_rate',
                'title': 'Great Savings Momentum!',
                'message': f"You've saved KES {recent_savings} in the last 30 days. Keep it up!",
                'priority': 'positive'
            })
        
        # Goal progress insights
        active_goals = goals.filter(status='active')
        if active_goals.exists():
            avg_progress = sum(goal.progress_percentage for goal in active_goals) / active_goals.count()
            
            if avg_progress > 75:
                insights.append({
                    'type': 'goal_progress',
                    'title': 'Excellent Progress!',
                    'message': f"Your average goal progress is {avg_progress:.1f}%. You're doing amazing!",
                    'priority': 'positive'
                })
            elif avg_progress < 25:
                insights.append({
                    'type': 'goal_progress',
                    'title': 'Time to Boost Your Savings',
                    'message': f"Your average goal progress is {avg_progress:.1f}%. Consider increasing your contributions.",
                    'priority': 'suggestion'
                })
        
        # Unallocated savings insight
        if savings_account.balance > 1000:
            insights.append({
                'type': 'unallocated_funds',
                'title': 'Unallocated Savings Available',
                'message': f"You have KES {savings_account.balance} in unallocated savings. Consider allocating to your goals.",
                'priority': 'suggestion'
            })
        
        logger.info(f"Generated {len(insights)} insights for user {user.username}")
        
        return {
            'user_id': user_id,
            'insights_count': len(insights),
            'insights': insights
        }
        
    except Exception as e:
        logger.error(f"Error generating savings insights for user {user_id}: {str(e)}")
        raise
