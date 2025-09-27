from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken
from project_apps.transactions.models import Transaction


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin
    """
    list_display = ('email', 'username', 'full_name', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('is_verified', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    User Profile admin
    """
    list_display = ('user', 'phone_number', 'preferred_currency', 'email_notifications', 'created_at')
    list_filter = ('preferred_currency', 'theme_preference', 'email_notifications', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone_number', 'date_of_birth', 'avatar')
        }),
        ('Preferences', {
            'fields': ('preferred_currency', 'theme_preference')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'sms_notifications', 'budget_alerts', 'bill_reminders')
        }),
        ('Financial Settings', {
            'fields': ('monthly_budget_limit', 'savings_goal_percentage')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Email Verification Token admin
    """
    list_display = ('user', 'token_preview', 'created_at', 'expires_at', 'is_used', 'is_expired')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'is_expired')
    
    def token_preview(self, obj):
        return f"{obj.token[:10]}..."
    token_preview.short_description = 'Token Preview'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Password Reset Token admin
    """
    list_display = ('user', 'token_preview', 'created_at', 'expires_at', 'is_used', 'is_expired')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('token', 'created_at', 'is_expired')
    
    def token_preview(self, obj):
        return f"{obj.token[:10]}..."
    token_preview.short_description = 'Token Preview'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

# Customize admin site
admin.site.site_header = "FinanceFlow Admin"
admin.site.site_title = "FinanceFlow Admin Portal"
admin.site.index_title = "Welcome to FinanceFlow Administration"
