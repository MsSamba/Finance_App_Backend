from django.db import models, transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import RecurringBill

class RecurringBillService:
    """Service class for recurring bill business logic"""
    
    @staticmethod
    def get_user_bill_stats(user):
        """Get comprehensive statistics for a user's bills"""
        bills = RecurringBill.objects.filter(user=user)
        
        # Calculate totals by frequency
        monthly_total = bills.filter(frequency='monthly').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        weekly_total = bills.filter(frequency='weekly').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        yearly_total = bills.filter(frequency='yearly').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Convert to monthly equivalent for comparison
        monthly_equivalent = (
            monthly_total + 
            (weekly_total * Decimal('4.33')) +  # Average weeks per month
            (yearly_total / Decimal('12'))
        )
        
        return {
            'total_monthly_bills': float(monthly_total),
            'total_weekly_bills': float(weekly_total),
            'total_yearly_bills': float(yearly_total),
            'monthly_equivalent': float(monthly_equivalent),
            'paid_count': bills.filter(paid=True).count(),
            'unpaid_count': bills.filter(paid=False).count(),
            'total_count': bills.count(),
            'overdue_count': RecurringBillService.get_overdue_bills(user).count(),
        }
    
    @staticmethod
    def get_overdue_bills(user):
        """Get bills that are overdue (past due date and not paid)"""
        today = timezone.now().date()
        return RecurringBill.objects.filter(
            user=user,
            paid=False,
            due_date__lt=today
        )
    
    @staticmethod
    def get_upcoming_bills(user, days_ahead=7):
        """Get bills due within the next specified days"""
        today = timezone.now().date()
        future_date = today + timedelta(days=days_ahead)
        
        return RecurringBill.objects.filter(
            user=user,
            paid=False,
            due_date__gte=today,
            due_date__lte=future_date
        )
    
    @staticmethod
    @transaction.atomic
    def bulk_mark_paid(user, bill_ids=None):
        """Mark bills as paid in bulk"""
        queryset = RecurringBill.objects.filter(user=user, paid=False)
        
        if bill_ids:
            queryset = queryset.filter(id__in=bill_ids)
        
        updated_count = queryset.update(paid=True)
        return updated_count
    
    @staticmethod
    @transaction.atomic
    def bulk_reset_bills(user, bill_ids=None):
        """Reset bills to unpaid status in bulk"""
        queryset = RecurringBill.objects.filter(user=user, paid=True)
        
        if bill_ids:
            queryset = queryset.filter(id__in=bill_ids)
        
        updated_count = queryset.update(paid=False)
        return updated_count
    
    @staticmethod
    def calculate_monthly_budget_impact(user):
        """Calculate the impact of recurring bills on monthly budget"""
        bills = RecurringBill.objects.filter(user=user)
        
        monthly_impact = Decimal('0.00')
        
        for bill in bills:
            if bill.frequency == 'monthly':
                monthly_impact += bill.amount
            elif bill.frequency == 'weekly':
                monthly_impact += bill.amount * Decimal('4.33')  # Average weeks per month
            elif bill.frequency == 'yearly':
                monthly_impact += bill.amount / Decimal('12')
        
        return float(monthly_impact)
    
    @staticmethod
    def get_payment_calendar(user, year=None, month=None):
        """Get a calendar view of when bills are due"""
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        bills = RecurringBill.objects.filter(
            user=user,
            due_date__year=year,
            due_date__month=month
        ).order_by('due_date')
        
        calendar_data = {}
        for bill in bills:
            day = bill.due_date.day
            if day not in calendar_data:
                calendar_data[day] = []
            
            calendar_data[day].append({
                'id': bill.id,
                'name': bill.name,
                'amount': float(bill.amount),
                'paid': bill.paid,
                'frequency': bill.frequency
            })
        
        return calendar_data
