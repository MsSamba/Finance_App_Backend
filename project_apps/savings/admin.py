from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum
from .models import (
    SavingsAccount, SavingsGoal, SavingsTransaction, SavingsAllocation,
    SavingsTemplate, SavingsSettings
)


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance_display', 'auto_save_percentage', 'is_auto_save_enabled', 'created_at']
    list_filter = ['is_auto_save_enabled', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'balance')
        }),
        ('Auto-Save Settings', {
            'fields': ('auto_save_percentage', 'is_auto_save_enabled')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def balance_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">KES {:,.2f}</span>',
            obj.balance
        )
    balance_display.short_description = 'Balance'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'target_amount', 'current_amount', 'progress_display',
        'status', 'priority', 'target_date', 'created_at'
    ]
    list_filter = ['status', 'priority', 'color', 'created_at', 'target_date']
    search_fields = ['name', 'user__username', 'user__email', 'description']
    readonly_fields = [
        'id', 'progress_percentage', 'remaining_amount', 'is_completed',
        'days_remaining', 'daily_saving_required', 'created_at', 'updated_at', 'completed_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'description', 'target_amount', 'current_amount')
        }),
        ('Settings', {
            'fields': ('color', 'status', 'priority', 'target_date')
        }),
        ('Auto-Allocation', {
            'fields': ('auto_allocate_enabled', 'auto_allocate_percentage'),
            'classes': ('collapse',)
        }),
        ('Progress Information', {
            'fields': (
                'progress_percentage', 'remaining_amount', 'is_completed',
                'days_remaining', 'daily_saving_required'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_completed', 'pause_goals', 'activate_goals']
    
    def progress_display(self, obj):
        percentage = obj.progress_percentage
        if percentage >= 100:
            color = 'green'
            icon = '✅'
        elif percentage >= 75:
            color = 'blue'
            icon = '🔵'
        elif percentage >= 50:
            color = 'orange'
            icon = '🟠'
        else:
            color = 'red'
            icon = '🔴'
        
        return format_html(
            '<span style="color: {};">{} {:.1f}%</span>',
            color, icon, percentage
        )
    progress_display.short_description = 'Progress'
    progress_display.admin_order_field = 'progress_percentage'
    
    def mark_as_completed(self, request, queryset):
        count = 0
        for goal in queryset:
            if goal.current_amount >= goal.target_amount:
                goal.status = 'completed'
                if not goal.completed_at:
                    goal.completed_at = timezone.now()
                goal.save()
                count += 1
        
        self.message_user(request, f'Marked {count} goals as completed.')
    mark_as_completed.short_description = 'Mark selected goals as completed'
    
    def pause_goals(self, request, queryset):
        count = queryset.update(status='paused')
        self.message_user(request, f'Paused {count} goals.')
    pause_goals.short_description = 'Pause selected goals'
    
    def activate_goals(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'Activated {count} goals.')
    activate_goals.short_description = 'Activate selected goals'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'savings_account', 'transaction_type', 'amount_display', 'description',
        'balance_after', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['savings_account__user__username', 'description']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('savings_account', 'transaction_type', 'amount', 'description')
        }),
        ('Balance Information', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Reference', {
            'fields': ('reference_transaction_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def amount_display(self, obj):
        color = 'green' if obj.transaction_type in ['deposit', 'auto_save'] else 'red'
        sign = '+' if obj.transaction_type in ['deposit', 'auto_save'] else '-'
        return format_html(
            '<span style="color: {};">{} KES {:,.2f}</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(savings_account__user=request.user)


@admin.register(SavingsAllocation)
class SavingsAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'savings_goal', 'allocation_type', 'amount_display', 'source',
        'balance_after', 'created_at'
    ]
    list_filter = ['allocation_type', 'source', 'created_at']
    search_fields = ['savings_goal__name', 'savings_goal__user__username', 'description']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Allocation Information', {
            'fields': ('savings_goal', 'allocation_type', 'amount', 'source', 'description')
        }),
        ('Balance Information', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def amount_display(self, obj):
        color = 'green' if obj.allocation_type == 'deposit' else 'red'
        sign = '+' if obj.allocation_type == 'deposit' else '-'
        return format_html(
            '<span style="color: {};">{} KES {:,.2f}</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(savings_goal__user=request.user)


@admin.register(SavingsTemplate)
class SavingsTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'suggested_amount', 'suggested_timeline_months',
        'priority', 'is_default', 'created_at'
    ]
    list_filter = ['category', 'priority', 'is_default', 'created_at']
    search_fields = ['name', 'description', 'category']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'category', 'is_default')
        }),
        ('Suggestions', {
            'fields': ('suggested_amount', 'suggested_timeline_months')
        }),
        ('Appearance', {
            'fields': ('color', 'priority')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_default', 'unmark_as_default']
    
    def mark_as_default(self, request, queryset):
        count = queryset.update(is_default=True)
        self.message_user(request, f'Marked {count} templates as default.')
    mark_as_default.short_description = 'Mark as default templates'
    
    def unmark_as_default(self, request, queryset):
        count = queryset.update(is_default=False)
        self.message_user(request, f'Unmarked {count} templates as default.')
    unmark_as_default.short_description = 'Unmark as default templates'


@admin.register(SavingsSettings)
class SavingsSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'auto_save_enabled', 'auto_save_percentage',
        'email_notifications', 'goal_reminders', 'created_at'
    ]
    list_filter = ['auto_save_enabled', 'email_notifications', 'goal_reminders', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Auto-Save Settings', {
            'fields': ('auto_save_enabled', 'auto_save_percentage')
        }),
        ('Notification Settings', {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications')
        }),
        ('Reminder Settings', {
            'fields': ('goal_reminders', 'monthly_reports', 'achievement_notifications')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
