from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db import models
from .models import Budget, BudgetHistory, BudgetAlert, BudgetTemplate, Category
from .serializers import (
    BudgetSerializer, BudgetHistorySerializer, BudgetAlertSerializer,
    BudgetTemplateSerializer, BudgetAnalyticsSerializer, BudgetSummarySerializer, CategorySerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing budget categories"""
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Return all categories"""
        return Category.objects.all()
    
    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """Create default categories"""
        default_categories = [
            {'name': 'Income', 'icon': '💰', 'is_income_category': True},
            {'name': 'Bills and Utilities', 'icon': '🏠', 'is_income_category': False},
            {'name': 'Education and Self Improvement', 'icon': '📚', 'is_income_category': False},
            {'name': 'Entertainment and Leisure', 'icon': '🎬', 'is_income_category': False},
            {'name': 'Family and Kids', 'icon': '👨‍👩‍👧‍👦', 'is_income_category': False},
            {'name': 'Food and Dining', 'icon': '🍽️', 'is_income_category': False},
            {'name': 'Health and Wellness', 'icon': '🏥', 'is_income_category': False},
            {'name': 'Savings and Investments', 'icon': '📈', 'is_income_category': False},
            {'name': 'Shopping and Personal Care', 'icon': '🛍️', 'is_income_category': False},
            {'name': 'Transportation', 'icon': '🚗', 'is_income_category': False},
        ]
        
        created_categories = []
        for cat_data in default_categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                created_categories.append(category)
        
        serializer = self.get_serializer(created_categories, many=True)
        return Response({
            'message': f'Created {len(created_categories)} default categories',
            'categories': serializer.data
        })



class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'period', 'status']

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def reset_spent(self, request, pk=None):
        """Reset the spent amount for a budget to zero"""
        budget = self.get_object()
        budget.reset_spent()
        
        serializer = self.get_serializer(budget)
        return Response({
            'message': f'Budget for {budget.category} has been reset to KES 0.',
            'budget': serializer.data
        })

    @action(detail=False, methods=['post'])
    def check_alerts(self, request):
        """Check all budgets for alert conditions and create alerts"""
        from .tasks import check_budget_alerts
        
        # Run alert check task
        result = check_budget_alerts.delay(request.user.id)
        
        return Response({
            'message': 'Budget alerts check initiated.',
            'task_id': result.id
        })

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get comprehensive budget analytics"""
        period = request.query_params.get('period', 'current')
        
        # Get user's active budgets
        budgets = self.get_queryset().filter(status='active')
        
        if not budgets.exists():
            return Response({
                'total_budgets': 0,
                'total_budget_limit': 0,
                'total_spent': 0,
                'total_remaining': 0,
                'overall_percentage_used': 0,
                'budgets_on_track': 0,
                'budgets_at_risk': 0,
                'budgets_exceeded': 0,
                'average_performance_score': 0,
                'category_performance': [],
                'period_comparison': [],
                'recommendations': []
            })

        # Calculate totals
        total_limit = budgets.aggregate(Sum('limit'))['limit__sum'] or Decimal('0')
        total_spent = budgets.aggregate(Sum('spent'))['spent__sum'] or Decimal('0')
        total_remaining = total_limit - total_spent
        overall_percentage = float((total_spent / total_limit * 100)) if total_limit > 0 else 0

        # Count budget statuses
        budgets_on_track = budgets.filter(
            spent__lte=models.F('limit') * models.F('alert_threshold') / 100
        ).count()
        budgets_at_risk = budgets.filter(
            spent__gt=models.F('limit') * models.F('alert_threshold') / 100,
            spent__lte=models.F('limit')
        ).count()
        budgets_exceeded = budgets.filter(spent__gt=models.F('limit')).count()

        # Calculate average performance score
        performance_scores = [budget.performance_score for budget in budgets]
        avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0

        # Category performance
        category_performance = []
        for budget in budgets:
            status = 'on_track'
            if budget.is_over_budget:
                status = 'exceeded'
            elif budget.is_alert_threshold_reached:
                status = 'at_risk'

            category_performance.append({
                'category': budget.category,
                'limit': float(budget.limit),
                'spent': float(budget.spent),
                'percentage_used': budget.percentage_used,
                'status': status,
                'color': budget.color,
                'performance_score': budget.performance_score
            })

        # Period comparison (last 6 periods)
        period_comparison = self._get_period_comparison(request.user, period)

        # Generate recommendations
        recommendations = self._generate_recommendations(budgets, overall_percentage, budgets_exceeded)

        analytics_data = {
            'total_budgets': budgets.count(),
            'total_budget_limit': float(total_limit),
            'total_spent': float(total_spent),
            'total_remaining': float(total_remaining),
            'overall_percentage_used': overall_percentage,
            'budgets_on_track': budgets_on_track,
            'budgets_at_risk': budgets_at_risk,
            'budgets_exceeded': budgets_exceeded,
            'average_performance_score': avg_performance,
            'category_performance': category_performance,
            'period_comparison': period_comparison,
            'recommendations': recommendations
        }

        return Response(analytics_data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get budget summary for current period"""
        budgets = self.get_queryset().filter(status='active')
        
        if not budgets.exists():
            return Response({
                'period': 'current',
                'total_budgets': 0,
                'total_limit': 0,
                'total_spent': 0,
                'total_remaining': 0,
                'percentage_used': 0,
                'performance_score': 0,
                'budgets_on_track': 0,
                'budgets_at_risk': 0,
                'budgets_exceeded': 0
            })

        # Calculate summary data
        total_limit = budgets.aggregate(Sum('limit'))['limit__sum'] or Decimal('0')
        total_spent = budgets.aggregate(Sum('spent'))['spent__sum'] or Decimal('0')
        total_remaining = total_limit - total_spent
        percentage_used = float((total_spent / total_limit * 100)) if total_limit > 0 else 0

        # Performance score
        performance_scores = [budget.performance_score for budget in budgets]
        avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0

        # Status counts
        budgets_on_track = sum(1 for b in budgets if not b.is_alert_threshold_reached)
        budgets_at_risk = sum(1 for b in budgets if b.is_alert_threshold_reached and not b.is_over_budget)
        budgets_exceeded = sum(1 for b in budgets if b.is_over_budget)

        summary_data = {
            'period': 'current',
            'total_budgets': budgets.count(),
            'total_limit': float(total_limit),
            'total_spent': float(total_spent),
            'total_remaining': float(total_remaining),
            'percentage_used': percentage_used,
            'performance_score': avg_performance,
            'budgets_on_track': budgets_on_track,
            'budgets_at_risk': budgets_at_risk,
            'budgets_exceeded': budgets_exceeded
        }

        return Response(summary_data)

    def _get_period_comparison(self, user, period_type):
        """Get historical period comparison data"""
        comparison_data = []
        
        # Get last 6 periods of history
        history_entries = BudgetHistory.objects.filter(
            budget__user=user
        ).order_by('-period_start')[:6]

        for entry in history_entries:
            comparison_data.append({
                'period': entry.period_start.strftime('%Y-%m'),
                'total_limit': float(entry.limit),
                'total_spent': float(entry.spent),
                'percentage_used': entry.percentage_used,
                'performance_score': float(entry.performance_score)
            })

        return comparison_data

    def _generate_recommendations(self, budgets, overall_percentage, exceeded_count):
        """Generate budget recommendations based on current performance"""
        recommendations = []

        if exceeded_count > 0:
            recommendations.append(
                f"You have {exceeded_count} budget(s) that are over limit. Consider reviewing your spending in these categories."
            )

        if overall_percentage > 90:
            recommendations.append(
                "You're using over 90% of your total budget. Consider reducing spending or increasing budget limits."
            )
        elif overall_percentage < 50:
            recommendations.append(
                "Great job! You're well within your budget limits. Consider setting aside the extra money for savings."
            )

        # Check for categories with high variance
        high_usage_budgets = [b for b in budgets if b.percentage_used > 80 and not b.is_over_budget]
        if high_usage_budgets:
            categories = [b.category for b in high_usage_budgets]
            recommendations.append(
                f"Watch your spending in {', '.join(categories)} - you're approaching your limits."
            )

        # Check for unused budgets
        low_usage_budgets = [b for b in budgets if b.percentage_used < 20]
        if len(low_usage_budgets) > 2:
            recommendations.append(
                "You have several budgets with low usage. Consider reallocating funds to categories where you need more budget."
            )

        if not recommendations:
            recommendations.append("Your budgets are well-balanced! Keep up the good financial management.")

        return recommendations


class BudgetHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BudgetHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['budget__category', 'period_start']

    def get_queryset(self):
        return BudgetHistory.objects.filter(budget__user=self.request.user)


class BudgetAlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BudgetAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['alert_type', 'is_read']

    def get_queryset(self):
        return BudgetAlert.objects.filter(budget__user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark an alert as read"""
        alert = self.get_object()
        alert.mark_as_read()
        
        serializer = self.get_serializer(alert)
        return Response({
            'message': 'Alert marked as read.',
            'alert': serializer.data
        })


class BudgetTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BudgetTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = BudgetTemplate.objects.all()

    @action(detail=True, methods=['post'])
    def apply_template(self, request, pk=None):
        """Apply a budget template to create budgets for the user"""
        template = self.get_object()
        user = request.user
        created_budgets = []
        errors = []

        for item in template.items.all():
            # Check if user already has an active budget for this category
            existing_budget = Budget.objects.filter(
                user=user,
                category=item.category,
                status='active'
            ).first()

            if existing_budget:
                errors.append(f"Budget for {item.category} already exists")
                continue

            # Create new budget from template item
            budget = Budget.objects.create(
                user=user,
                category=item.category,
                limit=item.limit,
                period=item.period,
                color=item.color,
                alert_threshold=item.alert_threshold,
                status='active'
            )
            created_budgets.append(budget)

        # Serialize created budgets
        budget_serializer = BudgetSerializer(created_budgets, many=True)

        return Response({
            'message': f'Applied template "{template.name}". Created {len(created_budgets)} budgets.',
            'created_budgets': budget_serializer.data,
            'errors': errors
        })
