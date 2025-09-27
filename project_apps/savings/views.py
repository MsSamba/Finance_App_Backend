from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from .models import (
    SavingsAccount, SavingsGoal, SavingsTransaction, SavingsAllocation,
    SavingsTemplate, SavingsSettings, SavingsReport
)
from .serializers import (
    SavingsAccountSerializer, SavingsGoalSerializer, SavingsTransactionSerializer,
    SavingsAllocationSerializer, SavingsTemplateSerializer, SavingsReportSerializer,
    SavingsSettingsSerializer, SavingsSummarySerializer,
    SavingsGoalActionSerializer, SavingsAccountActionSerializer
)


class SavingsAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for SavingsAccount model"""
    
    serializer_class = SavingsAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavingsAccount.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create savings account for current user"""
        account, created = SavingsAccount.objects.get_or_create(
            user=self.request.user,
            defaults={'balance': Decimal('0.00')}
        )
        return account
    
    @action(detail=False, methods=['get'])
    def my_account(self, request):
        """Get current user's savings account"""
        account = self.get_object()
        serializer = self.get_serializer(account)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def allocate_to_goal(self, request):
        """Allocate funds from savings account to a specific goal"""
        serializer = SavingsAccountActionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        goal_id = serializer.validated_data.get('goal_id')
        description = serializer.validated_data.get('description', '')
        
        # Get savings account
        account = self.get_object()
        
        # Check if sufficient funds available
        if not account.can_withdraw(amount):
            return Response({
                'error': f'Insufficient funds. Available balance: KES {account.balance}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get savings goal
        try:
            goal = SavingsGoal.objects.get(id=goal_id, user=request.user, status='active')
        except SavingsGoal.DoesNotExist:
            return Response({
                'error': 'Savings goal not found or inactive.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Perform the transfer
        if account.withdraw_funds(amount, f"Allocated to {goal.name}"):
            goal.add_funds(amount, source='transfer', description=description)
            
            return Response({
                'message': f'Successfully allocated KES {amount} to {goal.name}',
                'savings_balance': account.balance,
                'goal_balance': goal.current_amount
            })
        else:
            return Response({
                'error': 'Failed to allocate funds'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get savings account transaction history"""
        account = self.get_object()
        transactions = account.transactions.all()
        
        # Apply filters
        transaction_type = request.query_params.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # Date range filtering
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            transactions = transactions.filter(created_at__date__gte=date_from)
        if date_to:
            transactions = transactions.filter(created_at__date__lte=date_to)
        
        # Pagination
        limit = int(request.query_params.get('limit', 20))
        transactions = transactions[:limit]
        
        serializer = SavingsTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class SavingsGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for SavingsGoal model"""
    
    serializer_class = SavingsGoalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority', 'color']
    
    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_funds(self, request, pk=None):
        """Add funds to a savings goal"""
        goal = self.get_object()
        serializer = SavingsGoalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', '')
        
        # Add funds to goal
        if goal.add_funds(amount, source='manual', description=description):
            goal_serializer = self.get_serializer(goal)
            return Response({
                'message': f'Successfully added KES {amount} to {goal.name}',
                'goal': goal_serializer.data
            })
        else:
            return Response({
                'error': 'Failed to add funds to goal'
            }, status=status.HTTP_400_BAD_REQUEST)
        

    
    @action(detail=True, methods=['post'])
    def withdraw_funds(self, request, pk=None):
        """Withdraw funds from a savings goal"""
        goal = self.get_object()
        serializer = SavingsGoalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        description = serializer.validated_data.get('description', '')
        
        # Check if sufficient funds available
        if not goal.can_withdraw(amount):
            return Response({
                'error': f'Insufficient funds. Available balance: KES {goal.current_amount}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Withdraw funds from goal
        if goal.withdraw_funds(amount, description=description):
            # Add funds back to savings account
            account, _ = SavingsAccount.objects.get_or_create(user=request.user)
            account.add_funds(amount, f"Withdrawn from {goal.name}")
            
            goal_serializer = self.get_serializer(goal)
            return Response({
                'message': f'Successfully withdrew KES {amount} from {goal.name}',
                'goal': goal_serializer.data,
                'savings_balance': account.balance
            })
        else:
            return Response({
                'error': 'Failed to withdraw funds from goal'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get savings summary data"""
        user = request.user
        
        # Get savings account
        try:
            account = SavingsAccount.objects.get(user=user)
            total_balance = account.balance
        except SavingsAccount.DoesNotExist:
            total_balance = Decimal('0.00')
        
        # Get goals data
        goals = self.get_queryset().filter(status='active')
        allocated_balance = goals.aggregate(Sum('current_amount'))['current_amount__sum'] or Decimal('0')
        available_balance = total_balance
        
        total_target = goals.aggregate(Sum('target_amount'))['target_amount__sum'] or Decimal('0')
        overall_progress = float((allocated_balance / total_target * 100)) if total_target > 0 else 0
        
        completed_goals = self.get_queryset().filter(status='completed').count()
        
        # Calculate monthly savings rate
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        try:
            monthly_savings = SavingsTransaction.objects.filter(
                savings_account__user=user,
                transaction_type__in=['deposit', 'auto_save'],
                created_at__date__gte=month_start
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            # Assume monthly income (this could be calculated from income transactions)
            monthly_savings_rate = Decimal('20.00')  # Default 20%
        except:
            monthly_savings_rate = Decimal('0.00')
        
        summary_data = {
            'total_balance': float(total_balance),
            'available_balance': float(available_balance),
            'allocated_balance': float(allocated_balance),
            'total_goals': goals.count(),
            'completed_goals': completed_goals,
            'total_target': float(total_target),
            'overall_progress': overall_progress,
            'monthly_savings_rate': float(monthly_savings_rate)
        }
        
        return Response(summary_data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get detailed savings analytics"""
        user = request.user
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Get savings account
        try:
            account = SavingsAccount.objects.get(user=user)
        except SavingsAccount.DoesNotExist:
            return Response({
                'error': 'No savings account found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get goals
        goals = SavingsGoal.objects.filter(user=user)
        active_goals = goals.filter(status='active')
        
        # Calculate analytics
        analytics = {
            'total_balance': float(account.balance),
            'total_goals': goals.count(),
            'active_goals': active_goals.count(),
            'completed_goals': goals.filter(status='completed').count(),
            'paused_goals': goals.filter(status='paused').count(),
            
            # Progress analytics
            'average_progress': 0,
            'goals_on_track': 0,
            'goals_behind_schedule': 0,
            
            # Savings trends
            'savings_trend': [],
            'goal_completion_rate': 0,
            
            # Goal breakdown
            'goals_by_priority': {
                'urgent': active_goals.filter(priority='urgent').count(),
                'high': active_goals.filter(priority='high').count(),
                'medium': active_goals.filter(priority='medium').count(),
                'low': active_goals.filter(priority='low').count(),
            },
            
            # Monthly statistics
            'monthly_savings': 0,
            'monthly_allocations': 0,
            'monthly_withdrawals': 0,
        }
        
        # Calculate average progress
        if active_goals.exists():
            total_progress = sum(goal.progress_percentage for goal in active_goals)
            analytics['average_progress'] = total_progress / active_goals.count()
            
            # Goals on track vs behind schedule
            for goal in active_goals:
                if goal.target_date:
                    days_remaining = (goal.target_date - timezone.now().date()).days
                    if days_remaining > 0:
                        if goal.progress_percentage >= 50:  # Simple heuristic
                            analytics['goals_on_track'] += 1
                        else:
                            analytics['goals_behind_schedule'] += 1
        
        # Calculate completion rate
        total_goals = goals.count()
        if total_goals > 0:
            completed = goals.filter(status='completed').count()
            analytics['goal_completion_rate'] = (completed / total_goals) * 100
        
        # Get savings trend (last 30 days)
        for i in range(min(days, 30)):
            date = timezone.now().date() - timedelta(days=days-1-i)
            daily_savings = SavingsTransaction.objects.filter(
                savings_account=account,
                transaction_type__in=['deposit', 'auto_save'],
                created_at__date=date
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
            
            analytics['savings_trend'].append({
                'date': date.isoformat(),
                'amount': float(daily_savings)
            })
        
        # Monthly statistics
        month_start = timezone.now().date().replace(day=1)
        monthly_transactions = SavingsTransaction.objects.filter(
            savings_account=account,
            created_at__date__gte=month_start
        )
        
        analytics['monthly_savings'] = float(
            monthly_transactions.filter(
                transaction_type__in=['deposit', 'auto_save']
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        )
        
        analytics['monthly_allocations'] = float(
            monthly_transactions.filter(
                transaction_type='transfer_out'
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        )
        
        analytics['monthly_withdrawals'] = float(
            monthly_transactions.filter(
                transaction_type='withdrawal'
            ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        )
        
        return Response(analytics)


class SavingsTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SavingsTemplate model (read-only)"""
    
    serializer_class = SavingsTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SavingsTemplate.objects.all()
    
    @action(detail=True, methods=['post'])
    def apply_template(self, request, pk=None):
        """Apply a savings template to create a new goal"""
        template = self.get_object()
        user = request.user
        
        # Get custom data from request
        name = request.data.get('name', template.name)
        target_amount = request.data.get('target_amount', template.suggested_amount)
        target_date = request.data.get('target_date')
        
        if not target_amount:
            return Response({
                'error': 'Target amount is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for duplicate name
        if SavingsGoal.objects.filter(user=user, name=name, status='active').exists():
            return Response({
                'error': f'You already have an active savings goal named "{name}"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate target date if timeline provided
        calculated_target_date = target_date
        if not calculated_target_date and template.suggested_timeline_months:
            calculated_target_date = (
                timezone.now().date() + relativedelta(months=template.suggested_timeline_months)
            )
        
        # Create the savings goal
        goal = SavingsGoal.objects.create(
            user=user,
            name=name,
            description=template.description,
            target_amount=target_amount,
            color=template.color,
            priority=template.priority,
            target_date=calculated_target_date
        )
        
        goal_serializer = SavingsGoalSerializer(goal)
        return Response({
            'message': f'Successfully created savings goal "{name}" from template',
            'goal': goal_serializer.data
        })


class SavingsSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for SavingsSettings model"""
    
    serializer_class = SavingsSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavingsSettings.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create savings settings for current user"""
        settings, created = SavingsSettings.objects.get_or_create(
            user=self.request.user,
            defaults={
                'auto_save_enabled': True,
                'auto_save_percentage': Decimal('20.00')
            }
        )
        return settings
    
    @action(detail=False, methods=['get'])
    def my_settings(self, request):
        """Get current user's savings settings"""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_settings(self, request):
        """Update current user's savings settings"""
        settings = self.get_object()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Savings settings updated successfully',
            'settings': serializer.data
        })


class SavingsReportViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SavingsReport model (read-only)"""
    
    serializer_class = SavingsReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavingsReport.objects.filter(user=self.request.user)


class SavingsTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SavingsTransaction model (read-only)"""
    
    serializer_class = SavingsTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['transaction_type', 'savings_goal']
    
    def get_queryset(self):
        return SavingsTransaction.objects.filter(
            savings_account__user=self.request.user
        ).order_by('-created_at')


class SavingsAllocationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for SavingsAllocation model (read-only)"""
    
    serializer_class = SavingsAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavingsAllocation.objects.filter(
            savings_goal__user=self.request.user
        ).order_by('-created_at')


class SavingsAnalyticsView(APIView):
    """API view for comprehensive savings analytics"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get detailed savings analytics data"""
        user = request.user
        
        # Get date range from query params
        period = request.query_params.get('period', '30d')  # 7d, 30d, 90d, 1y
        
        if period == '7d':
            days = 7
            start_date = timezone.now().date() - timedelta(days=7)
        elif period == '30d':
            days = 30
            start_date = timezone.now().date() - timedelta(days=30)
        elif period == '90d':
            days = 90
            start_date = timezone.now().date() - timedelta(days=90)
        elif period == '1y':
            days = 365
            start_date = timezone.now().date() - timedelta(days=365)
        else:
            days = 30
            start_date = timezone.now().date() - timedelta(days=30)
        
        # Get savings account
        try:
            account = SavingsAccount.objects.get(user=user)
        except SavingsAccount.DoesNotExist:
            return Response({
                'error': 'No savings account found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get goals
        goals = SavingsGoal.objects.filter(user=user)
        active_goals = goals.filter(status='active')
        
        # Base analytics
        analytics = {
            'period': period,
            'total_balance': float(account.balance),
            'goals': {
                'total': goals.count(),
                'active': active_goals.count(),
                'completed': goals.filter(status='completed').count(),
                'paused': goals.filter(status='paused').count(),
            },
            'progress': {
                'average_progress': 0,
                'goals_on_track': 0,
                'goals_behind_schedule': 0,
                'completion_rate': 0,
            },
            'savings_patterns': {
                'total_saved': 0,
                'average_daily': 0,
                'best_day': None,
                'consistency_score': 0,
            },
            'goal_breakdown': {
                'by_priority': {
                    'urgent': active_goals.filter(priority='urgent').count(),
                    'high': active_goals.filter(priority='high').count(),
                    'medium': active_goals.filter(priority='medium').count(),
                    'low': active_goals.filter(priority='low').count(),
                },
                'by_status': {
                    'on_track': 0,
                    'at_risk': 0,
                    'behind': 0,
                }
            },
            'trends': {
                'daily_savings': [],
                'weekly_savings': [],
                'monthly_savings': [],
            },
            'predictions': {
                'projected_monthly_savings': 0,
                'goals_likely_to_complete': 0,
                'estimated_completion_dates': [],
            }
        }
        
        # Calculate progress metrics
        if active_goals.exists():
            total_progress = sum(goal.progress_percentage for goal in active_goals)
            analytics['progress']['average_progress'] = total_progress / active_goals.count()
            
            # Analyze goal status
            for goal in active_goals:
                progress = goal.progress_percentage
                if goal.target_date:
                    days_remaining = (goal.target_date - timezone.now().date()).days
                    if days_remaining > 0:
                        expected_progress = 100 - (days_remaining / (goal.target_date - goal.created_at.date()).days * 100)
                        
                        if progress >= expected_progress * 0.9:  # Within 10% of expected
                            analytics['progress']['goals_on_track'] += 1
                            analytics['goal_breakdown']['by_status']['on_track'] += 1
                        elif progress >= expected_progress * 0.7:  # Within 30% of expected
                            analytics['goal_breakdown']['by_status']['at_risk'] += 1
                        else:
                            analytics['progress']['goals_behind_schedule'] += 1
                            analytics['goal_breakdown']['by_status']['behind'] += 1
                else:
                    # No target date - use simple progress thresholds
                    if progress >= 70:
                        analytics['progress']['goals_on_track'] += 1
                        analytics['goal_breakdown']['by_status']['on_track'] += 1
                    elif progress >= 40:
                        analytics['goal_breakdown']['by_status']['at_risk'] += 1
                    else:
                        analytics['progress']['goals_behind_schedule'] += 1
                        analytics['goal_breakdown']['by_status']['behind'] += 1
        
        # Calculate completion rate
        total_goals = goals.count()
        if total_goals > 0:
            completed = goals.filter(status='completed').count()
            analytics['progress']['completion_rate'] = (completed / total_goals) * 100
        
        # Analyze savings patterns
        transactions = SavingsTransaction.objects.filter(
            savings_account=account,
            transaction_type__in=['deposit', 'auto_save'],
            created_at__date__gte=start_date
        )
        
        total_saved = transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        analytics['savings_patterns']['total_saved'] = float(total_saved)
        analytics['savings_patterns']['average_daily'] = float(total_saved / days) if days > 0 else 0
        
        # Find best savings day
        daily_totals = {}
        for transaction in transactions:
            date_key = transaction.created_at.date()
            if date_key not in daily_totals:
                daily_totals[date_key] = Decimal('0')
            daily_totals[date_key] += transaction.amount
        
        if daily_totals:
            best_day = max(daily_totals.items(), key=lambda x: x[1])
            analytics['savings_patterns']['best_day'] = {
                'date': best_day[0].isoformat(),
                'amount': float(best_day[1])
            }
            
            # Calculate consistency score (percentage of days with savings activity)
            days_with_savings = len(daily_totals)
            analytics['savings_patterns']['consistency_score'] = (days_with_savings / days) * 100
        
        # Generate trend data
        # Daily trend
        for i in range(min(days, 30)):  # Last 30 days max for daily
            date = timezone.now().date() - timedelta(days=min(days, 30)-1-i)
            daily_amount = daily_totals.get(date, Decimal('0'))
            analytics['trends']['daily_savings'].append({
                'date': date.isoformat(),
                'amount': float(daily_amount)
            })
        
        # Weekly trend
        for i in range(min(days // 7, 12)):  # Last 12 weeks max
            week_start = timezone.now().date() - timedelta(weeks=min(days // 7, 12)-i)
            week_end = week_start + timedelta(days=6)
            
            weekly_amount = sum(
                amount for date, amount in daily_totals.items()
                if week_start <= date <= week_end
            )
            
            analytics['trends']['weekly_savings'].append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'amount': float(weekly_amount)
            })
        
        # Monthly trend
        current_date = timezone.now().date()
        for i in range(min(days // 30, 12)):  # Last 12 months max
            month_start = (current_date - relativedelta(months=min(days // 30, 12)-1-i)).replace(day=1)
            if i == 0:
                month_end = current_date
            else:
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            monthly_amount = sum(
                amount for date, amount in daily_totals.items()
                if month_start <= date <= month_end
            )
            
            analytics['trends']['monthly_savings'].append({
                'month': month_start.strftime('%Y-%m'),
                'amount': float(monthly_amount)
            })
        
        # Generate predictions
        if len(analytics['trends']['monthly_savings']) >= 2:
            # Simple linear projection based on recent trend
            recent_months = analytics['trends']['monthly_savings'][-3:]
            avg_monthly = sum(m['amount'] for m in recent_months) / len(recent_months)
            analytics['predictions']['projected_monthly_savings'] = avg_monthly
            
            # Estimate goals likely to complete
            for goal in active_goals:
                if goal.target_date and avg_monthly > 0:
                    months_to_target = (goal.target_date - timezone.now().date()).days / 30
                    projected_amount = goal.current_amount + (avg_monthly * months_to_target * 0.3)  # Assume 30% goes to this goal
                    
                    if projected_amount >= goal.target_amount:
                        analytics['predictions']['goals_likely_to_complete'] += 1
                        
                        # Estimate completion date
                        remaining = goal.target_amount - goal.current_amount
                        monthly_allocation = avg_monthly * 0.3  # Rough estimate
                        if monthly_allocation > 0:
                            months_needed = float(remaining) / monthly_allocation
                            completion_date = timezone.now().date() + relativedelta(months=int(months_needed))
                            
                            analytics['predictions']['estimated_completion_dates'].append({
                                'goal_id': goal.id,
                                'goal_name': goal.name,
                                'estimated_date': completion_date.isoformat(),
                                'confidence': 'medium' if months_needed <= months_to_target else 'low'
                            })
        
        return Response(analytics)


class SavingsSummaryView(APIView):
    """API view for savings summary dashboard"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get savings summary data for dashboard"""
        user = request.user
        
        # Get savings account
        try:
            account = SavingsAccount.objects.get(user=user)
            total_balance = account.balance
        except SavingsAccount.DoesNotExist:
            total_balance = Decimal('0.00')
        
        # Get goals data
        goals = SavingsGoal.objects.filter(user=user)
        active_goals = goals.filter(status='active')
        
        allocated_balance = active_goals.aggregate(
            Sum('current_amount')
        )['current_amount__sum'] or Decimal('0')
        
        available_balance = total_balance
        total_target = active_goals.aggregate(
            Sum('target_amount')
        )['target_amount__sum'] or Decimal('0')
        
        overall_progress = float((allocated_balance / total_target * 100)) if total_target > 0 else 0
        
        completed_goals = goals.filter(status='completed').count()
        
        # Calculate monthly savings rate
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        monthly_savings = SavingsTransaction.objects.filter(
            savings_account__user=user,
            transaction_type__in=['deposit', 'auto_save'],
            created_at__date__gte=month_start
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        
        # Get recent activity (last 5 transactions)
        recent_activity = SavingsTransaction.objects.filter(
            savings_account__user=user
        ).order_by('-created_at')[:5]
        
        activity_data = []
        for transaction in recent_activity:
            activity_data.append({
                'id': transaction.id,
                'type': transaction.transaction_type,
                'amount': float(transaction.amount),
                'description': transaction.description,
                'created_at': transaction.created_at.isoformat(),
                'goal_name': transaction.savings_goal.name if transaction.savings_goal else None
            })
        
        summary_data = {
            'total_balance': float(total_balance),
            'available_balance': float(available_balance),
            'allocated_balance': float(allocated_balance),
            'total_goals': active_goals.count(),
            'completed_goals': completed_goals,
            'total_target': float(total_target),
            'overall_progress': overall_progress,
            'monthly_savings': float(monthly_savings),
            'recent_activity': activity_data,
            'top_goals': [],
        }
        
        # Get top 3 goals by progress
        top_goals = active_goals.order_by('-current_amount')[:3]
        for goal in top_goals:
            summary_data['top_goals'].append({
                'id': goal.id,
                'name': goal.name,
                'current_amount': float(goal.current_amount),
                'target_amount': float(goal.target_amount),
                'progress_percentage': goal.progress_percentage,
                'color': goal.color,
                'priority': goal.priority
            })
        
        return Response(summary_data)


class SavingsInsightsView(APIView):
    """API view for personalized savings insights and recommendations"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get personalized savings insights"""
        user = request.user
        insights = []
        
        # Get user data
        try:
            account = SavingsAccount.objects.get(user=user)
        except SavingsAccount.DoesNotExist:
            return Response({'insights': []})
        
        goals = SavingsGoal.objects.filter(user=user)
        active_goals = goals.filter(status='active')
        
        # Insight 1: Unallocated savings
        if account.balance > 1000:
            insights.append({
                'type': 'unallocated_funds',
                'title': 'Unallocated Savings Available',
                'message': f'You have KES {account.balance} in unallocated savings. Consider creating goals or allocating to existing ones.',
                'priority': 'medium',
                'action': 'allocate_funds',
                'action_data': {'amount': float(account.balance)}
            })
        
        # Insight 2: Goal progress
        if active_goals.exists():
            avg_progress = sum(goal.progress_percentage for goal in active_goals) / active_goals.count()
            
            if avg_progress > 80:
                insights.append({
                    'type': 'excellent_progress',
                    'title': 'Excellent Progress!',
                    'message': f'Your average goal progress is {avg_progress:.1f}%. You\'re doing great!',
                    'priority': 'positive',
                    'action': 'keep_going'
                })
            elif avg_progress < 30:
                insights.append({
                    'type': 'slow_progress',
                    'title': 'Consider Boosting Your Savings',
                    'message': f'Your average goal progress is {avg_progress:.1f}%. Consider increasing your contributions.',
                    'priority': 'suggestion',
                    'action': 'increase_savings'
                })
        
        # Insight 3: Approaching deadlines
        approaching_deadlines = active_goals.filter(
            target_date__lte=timezone.now().date() + timedelta(days=30),
            target_date__gte=timezone.now().date()
        )
        
        if approaching_deadlines.exists():
            goal_names = [goal.name for goal in approaching_deadlines[:2]]
            insights.append({
                'type': 'approaching_deadline',
                'title': 'Goals Approaching Deadline',
                'message': f'{approaching_deadlines.count()} goal(s) have deadlines in the next 30 days: {", ".join(goal_names)}',
                'priority': 'urgent',
                'action': 'review_goals',
                'action_data': {'goal_ids': [goal.id for goal in approaching_deadlines]}
            })
        
        # Insight 4: Savings streak
        last_7_days = timezone.now().date() - timedelta(days=7)
        recent_savings = SavingsTransaction.objects.filter(
            savings_account=account,
            transaction_type__in=['deposit', 'auto_save'],
            created_at__date__gte=last_7_days
        ).count()
        
        if recent_savings >= 5:
            insights.append({
                'type': 'savings_streak',
                'title': 'Great Savings Streak!',
                'message': f'You\'ve made {recent_savings} savings transactions in the last 7 days. Keep it up!',
                'priority': 'positive',
                'action': 'maintain_streak'
            })
        elif recent_savings == 0:
            insights.append({
                'type': 'no_recent_activity',
                'title': 'No Recent Savings Activity',
                'message': 'You haven\'t saved any money in the last 7 days. Consider setting up automatic savings.',
                'priority': 'suggestion',
                'action': 'enable_auto_save'
            })
        
        # Insight 5: Goal recommendations
        if active_goals.count() < 3:
            insights.append({
                'type': 'goal_recommendation',
                'title': 'Consider Adding More Goals',
                'message': 'Having multiple savings goals can help you stay motivated and organized.',
                'priority': 'suggestion',
                'action': 'create_goal'
            })
        
        # Insight 6: High priority goals without progress
        stagnant_goals = active_goals.filter(
            priority__in=['urgent', 'high'],
            current_amount=0
        )
        
        if stagnant_goals.exists():
            insights.append({
                'type': 'stagnant_priority_goals',
                'title': 'High Priority Goals Need Attention',
                'message': f'{stagnant_goals.count()} high-priority goal(s) haven\'t received any funds yet.',
                'priority': 'urgent',
                'action': 'fund_priority_goals',
                'action_data': {'goal_ids': [goal.id for goal in stagnant_goals]}
            })
        
        return Response({
            'insights': insights,
            'insights_count': len(insights)
        })
