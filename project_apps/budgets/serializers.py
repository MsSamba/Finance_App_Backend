# from rest_framework import serializers
# from .models import Budget, BudgetHistory, BudgetAlert, BudgetTemplate, BudgetTemplateItem, Category
# from django.utils import timezone


# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Category
#         fields = ['id', 'name', 'icon', 'is_income_category', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'created_at', 'updated_at']


# class BudgetSerializer(serializers.ModelSerializer):
#     remaining = serializers.ReadOnlyField()
#     percentage_used = serializers.ReadOnlyField()
#     is_over_budget = serializers.ReadOnlyField()
#     is_alert_threshold_reached = serializers.ReadOnlyField()
#     is_current_period = serializers.ReadOnlyField()
#     days_remaining = serializers.ReadOnlyField()
#     performance_score = serializers.ReadOnlyField()

#     class Meta:
#         model = Budget
#         fields = [
#             'id', 'category', 'limit', 'spent', 'period', 'color',
#             'alert_threshold', 'email_alerts', 'sms_alerts', 'status',
#             'period_start', 'period_end', 'created_at', 'updated_at',
#             'remaining', 'percentage_used', 'is_over_budget',
#             'is_alert_threshold_reached', 'is_current_period',
#             'days_remaining', 'performance_score'
#         ]
#         read_only_fields = ['id', 'spent', 'period_start', 'period_end', 'created_at', 'updated_at']

#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         return super().create(validated_data)

#     def validate_category(self, value):
#         user = self.context['request'].user
        
#         # Check if user already has an active budget for this category
#         if self.instance is None:  # Creating new budget
#             existing = Budget.objects.filter(
#                 user=user,
#                 category=value,
#                 status='active'
#             ).exists()
#             if existing:
#                 raise serializers.ValidationError(
#                     f"You already have an active budget for {value}. Please edit the existing budget or set it to inactive."
#                 )
#         else:  # Updating existing budget
#             existing = Budget.objects.filter(
#                 user=user,
#                 category=value,
#                 status='active'
#             ).exclude(id=self.instance.id).exists()
#             if existing:
#                 raise serializers.ValidationError(
#                     f"You already have an active budget for {value}."
#                 )
        
#         return value

#     def validate_limit(self, value):
#         if value <= 0:
#             raise serializers.ValidationError("Budget limit must be greater than 0.")
#         return value

#     def validate_alert_threshold(self, value):
#         if not (0 <= value <= 100):
#             raise serializers.ValidationError("Alert threshold must be between 0 and 100.")
#         return value


# class BudgetHistorySerializer(serializers.ModelSerializer):
#     category = serializers.CharField(source='budget.category', read_only=True)
#     color = serializers.CharField(source='budget.color', read_only=True)
#     percentage_used = serializers.ReadOnlyField()
#     remaining = serializers.ReadOnlyField()

#     class Meta:
#         model = BudgetHistory
#         fields = [
#             'id', 'category', 'color', 'period_start', 'period_end',
#             'limit', 'spent', 'percentage_used', 'remaining',
#             'performance_score', 'created_at'
#         ]


# class BudgetAlertSerializer(serializers.ModelSerializer):
#     category = serializers.CharField(source='budget.category', read_only=True)
#     budget_id = serializers.UUIDField(source='budget.id', read_only=True)

#     class Meta:
#         model = BudgetAlert
#         fields = [
#             'id', 'budget_id', 'category', 'alert_type', 'message',
#             'is_read', 'email_sent', 'sms_sent', 'created_at'
#         ]


# class BudgetTemplateItemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = BudgetTemplateItem
#         fields = ['category', 'limit', 'period', 'color', 'alert_threshold']


# class BudgetTemplateSerializer(serializers.ModelSerializer):
#     items = BudgetTemplateItemSerializer(many=True, read_only=True)
#     items_count = serializers.SerializerMethodField()

#     class Meta:
#         model = BudgetTemplate
#         fields = ['id', 'name', 'description', 'is_default', 'items_count', 'items', 'created_at']

#     def get_items_count(self, obj):
#         return obj.items.count()


# class BudgetAnalyticsSerializer(serializers.Serializer):
#     total_budgets = serializers.IntegerField()
#     total_budget_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
#     overall_percentage_used = serializers.FloatField()
#     budgets_on_track = serializers.IntegerField()
#     budgets_at_risk = serializers.IntegerField()
#     budgets_exceeded = serializers.IntegerField()
#     average_performance_score = serializers.FloatField()
#     category_performance = serializers.ListField()
#     period_comparison = serializers.ListField()
#     recommendations = serializers.ListField()


# class BudgetSummarySerializer(serializers.Serializer):
#     period = serializers.CharField()
#     total_budgets = serializers.IntegerField()
#     total_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
#     total_remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
#     percentage_used = serializers.FloatField()
#     performance_score = serializers.FloatField()
#     budgets_on_track = serializers.IntegerField()
#     budgets_at_risk = serializers.IntegerField()
#     budgets_exceeded = serializers.IntegerField()


from rest_framework import serializers
from .models import Budget, BudgetHistory, BudgetAlert, BudgetTemplate, BudgetTemplateItem
from project_apps.transactions.models import Category
from django.utils import timezone
from decimal import Decimal

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'is_income_category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class BudgetSerializer(serializers.ModelSerializer):
    remaining = serializers.ReadOnlyField()
    percentage_used = serializers.ReadOnlyField()
    is_over_budget = serializers.ReadOnlyField()
    is_alert_threshold_reached = serializers.ReadOnlyField()
    is_current_period = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    performance_score = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'limit', 'spent', 'period', 'color',
            'alert_threshold', 'email_alerts', 'sms_alerts', 'status',
            'period_start', 'period_end', 'created_at', 'updated_at',
            'remaining', 'percentage_used', 'is_over_budget',
            'is_alert_threshold_reached', 'is_current_period',
            'days_remaining', 'performance_score'
        ]
        read_only_fields = ['id', 'spent', 'period_start', 'period_end', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        
        user = validated_data['user']
        budget_limit = validated_data['limit']
        
        # Calculate current balance from transactions
        current_balance = self._calculate_current_balance(user)
        
        if current_balance < budget_limit:
            raise serializers.ValidationError({
                'limit': f'Insufficient balance. Current balance: KES {current_balance}, Budget limit: KES {budget_limit}'
            })
        
        return super().create(validated_data)

    def _calculate_current_balance(self, user):
        """Calculate user's current balance from transactions"""
        from project_apps.transactions.models import Transaction
        from django.db.models import Sum, Q
        from django.db.models.functions import Coalesce
        
        income_total = Transaction.objects.filter(
            user=user, type='income'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        expense_total = Transaction.objects.filter(
            user=user, type='expense'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        # Subtract existing budget allocations
        allocated_budgets = Budget.objects.filter(
            user=user, status='active'
        ).aggregate(total=Coalesce(Sum('limit'), Decimal('0')))['total']
        
        return income_total - expense_total - allocated_budgets

    def validate_category(self, value):
        user = self.context['request'].user
        
        # Check if user already has an active budget for this category
        if self.instance is None:  # Creating new budget
            existing = Budget.objects.filter(
                user=user,
                category=value,
                status='active'
            ).exists()
            if existing:
                raise serializers.ValidationError(
                    f"You already have an active budget for {value}. Please edit the existing budget or set it to inactive."
                )
        else:  # Updating existing budget
            existing = Budget.objects.filter(
                user=user,
                category=value,
                status='active'
            ).exclude(id=self.instance.id).exists()
            if existing:
                raise serializers.ValidationError(
                    f"You already have an active budget for {value}."
                )
        
        return value

    def validate_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget limit must be greater than 0.")
        return value

    def validate_alert_threshold(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Alert threshold must be between 0 and 100.")
        return value


class BudgetHistorySerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='budget.category', read_only=True)
    color = serializers.CharField(source='budget.color', read_only=True)
    percentage_used = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()

    class Meta:
        model = BudgetHistory
        fields = [
            'id', 'category', 'color', 'period_start', 'period_end',
            'limit', 'spent', 'percentage_used', 'remaining',
            'performance_score', 'created_at'
        ]


class BudgetAlertSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='budget.category', read_only=True)
    budget_id = serializers.UUIDField(source='budget.id', read_only=True)

    class Meta:
        model = BudgetAlert
        fields = [
            'id', 'budget_id', 'category', 'alert_type', 'message',
            'is_read', 'email_sent', 'sms_sent', 'created_at'
        ]


class BudgetTemplateItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetTemplateItem
        fields = ['category', 'limit', 'period', 'color', 'alert_threshold']


class BudgetTemplateSerializer(serializers.ModelSerializer):
    items = BudgetTemplateItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = BudgetTemplate
        fields = ['id', 'name', 'description', 'is_default', 'items_count', 'items', 'created_at']

    def get_items_count(self, obj):
        return obj.items.count()


class BudgetAnalyticsSerializer(serializers.Serializer):
    total_budgets = serializers.IntegerField()
    total_budget_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    overall_percentage_used = serializers.FloatField()
    budgets_on_track = serializers.IntegerField()
    budgets_at_risk = serializers.IntegerField()
    budgets_exceeded = serializers.IntegerField()
    average_performance_score = serializers.FloatField()
    category_performance = serializers.ListField()
    period_comparison = serializers.ListField()
    recommendations = serializers.ListField()


class BudgetSummarySerializer(serializers.Serializer):
    period = serializers.CharField()
    total_budgets = serializers.IntegerField()
    total_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage_used = serializers.FloatField()
    performance_score = serializers.FloatField()
    budgets_on_track = serializers.IntegerField()
    budgets_at_risk = serializers.IntegerField()
    budgets_exceeded = serializers.IntegerField()

