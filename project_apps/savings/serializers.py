from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    SavingsAccount, SavingsGoal, SavingsTransaction, SavingsAllocation,
    SavingsTemplate, SavingsSettings, SavingsReport
)
from decimal import Decimal


class SavingsAccountSerializer(serializers.ModelSerializer):
    """Serializer for SavingsAccount model"""
    
    class Meta:
        model = SavingsAccount
        fields = [
            'id', 'balance', 'auto_save_percentage', 'is_auto_save_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SavingsGoalSerializer(serializers.ModelSerializer):
    """Serializer for SavingsGoal model"""
    
    # Read-only computed fields
    remaining_amount = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    daily_saving_required = serializers.ReadOnlyField()
    
    class Meta:
        model = SavingsGoal
        fields = [
            'id', 'name', 'description', 'target_amount', 'current_amount',
            'color', 'status', 'priority', 'target_date',
            'auto_allocate_enabled', 'auto_allocate_percentage',
            'remaining_amount', 'progress_percentage', 'is_completed',
            'days_remaining', 'daily_saving_required',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'current_amount', 'completed_at', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Target amount must be greater than 0.")
        return value
    
    def validate_auto_allocate_percentage(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Auto-allocate percentage must be between 0 and 100.")
        return value
    
    def validate_name(self, value):
        user = self.context['request'].user
        
        # Check for duplicate names (excluding current instance if updating)
        queryset = SavingsGoal.objects.filter(user=user, name=value, status='active')
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "You already have an active savings goal with this name."
            )
        
        return value


class SavingsTransactionSerializer(serializers.ModelSerializer):
    """Serializer for SavingsTransaction model"""
    
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = SavingsTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount',
            'description', 'balance_before', 'balance_after',
            'reference_transaction_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SavingsAllocationSerializer(serializers.ModelSerializer):
    """Serializer for SavingsAllocation model"""
    
    allocation_type_display = serializers.CharField(source='get_allocation_type_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    goal_name = serializers.CharField(source='savings_goal.name', read_only=True)
    
    class Meta:
        model = SavingsAllocation
        fields = [
            'id', 'goal_name', 'amount', 'allocation_type', 'allocation_type_display',
            'source', 'source_display', 'description', 'balance_before',
            'balance_after', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SavingsTemplateSerializer(serializers.ModelSerializer):
    """Serializer for SavingsTemplate model"""
    
    class Meta:
        model = SavingsTemplate
        fields = [
            'id', 'name', 'description', 'suggested_amount',
            'suggested_timeline_months', 'color', 'priority',
            'is_default', 'category', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SavingsReportSerializer(serializers.ModelSerializer):
    """Serializer for SavingsReport model"""
    
    savings_rate = serializers.SerializerMethodField()
    withdrawal_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = SavingsReport
        fields = [
            'id', 'report_date', 'period_start', 'period_end',
            'total_saved', 'auto_saved', 'manual_saved', 'total_withdrawn',
            'net_savings', 'goals_completed', 'goals_in_progress',
            'average_goal_progress', 'savings_rate', 'withdrawal_rate',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_savings_rate(self, obj):
        """Calculate savings rate percentage"""
        if obj.total_saved == 0:
            return 0.0
        return float((obj.net_savings / obj.total_saved) * 100)
    
    def get_withdrawal_rate(self, obj):
        """Calculate withdrawal rate percentage"""
        if obj.total_saved == 0:
            return 0.0
        return float((obj.total_withdrawn / obj.total_saved) * 100)


class SavingsSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SavingsSettings model"""
    
    class Meta:
        model = SavingsSettings
        fields = [
            'auto_save_enabled', 'auto_save_percentage',
            'email_notifications', 'sms_notifications', 'push_notifications',
            'goal_reminders', 'monthly_reports', 'achievement_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SavingsGoalActionSerializer(serializers.Serializer):
    """Serializer for savings goal actions (add/withdraw funds)"""
    
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value


class SavingsAccountActionSerializer(serializers.Serializer):
    """Serializer for savings account actions"""
    
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    goal_id = serializers.UUIDField(required=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
    
    def validate_goal_id(self, value):
        if value:
            user = self.context['request'].user
            if not SavingsGoal.objects.filter(id=value, user=user, status='active').exists():
                raise serializers.ValidationError("Invalid savings goal selected.")
        return value


class SavingsSummarySerializer(serializers.Serializer):
    """Serializer for savings summary data"""
    
    total_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    available_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    allocated_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_goals = serializers.IntegerField()
    completed_goals = serializers.IntegerField()
    total_target = serializers.DecimalField(max_digits=12, decimal_places=2)
    overall_progress = serializers.FloatField()
    monthly_savings_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
