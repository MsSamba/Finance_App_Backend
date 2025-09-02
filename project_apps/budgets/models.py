from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta



class Category(models.Model):
    """Budget categories - simplified to match frontend"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=10, default='💰')
    is_income_category = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"


class Budget(models.Model):
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    COLOR_CHOICES = [
        ('bg-blue-500', 'Blue'),
        ('bg-green-500', 'Green'),
        ('bg-purple-500', 'Purple'),
        ('bg-red-500', 'Red'),
        ('bg-yellow-500', 'Yellow'),
        ('bg-indigo-500', 'Indigo'),
        ('bg-pink-500', 'Pink'),
        ('bg-gray-500', 'Gray'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='monthly')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='bg-blue-500')
    alert_threshold = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('80.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    email_alerts = models.BooleanField(default=True)
    sms_alerts = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Period tracking
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_alert_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'category', 'status']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['period_start', 'period_end']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category} ({self.period})"

    def save(self, *args, **kwargs):
        if not self.period_start or not self.period_end:
            self.set_period_dates()
        super().save(*args, **kwargs)

    def set_period_dates(self):
        """Set period start and end dates based on period type"""
        now = timezone.now()
        
        if self.period == 'monthly':
            self.period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            self.period_end = (self.period_start + relativedelta(months=1)) - timedelta(seconds=1)
        elif self.period == 'quarterly':
            quarter = (now.month - 1) // 3 + 1
            quarter_start_month = (quarter - 1) * 3 + 1
            self.period_start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            self.period_end = (self.period_start + relativedelta(months=3)) - timedelta(seconds=1)
        elif self.period == 'yearly':
            self.period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            self.period_end = (self.period_start + relativedelta(years=1)) - timedelta(seconds=1)

    @property
    def remaining(self):
        """Calculate remaining budget amount"""
        return self.limit - self.spent

    @property
    def percentage_used(self):
        """Calculate percentage of budget used"""
        if self.limit == 0:
            return 0
        return float((self.spent / self.limit) * 100)

    @property
    def is_over_budget(self):
        """Check if budget is exceeded"""
        return self.spent > self.limit

    @property
    def is_alert_threshold_reached(self):
        """Check if alert threshold is reached"""
        return self.percentage_used >= float(self.alert_threshold)

    @property
    def is_current_period(self):
        """Check if budget is in current period"""
        now = timezone.now()
        return self.period_start <= now <= self.period_end

    @property
    def days_remaining(self):
        """Calculate days remaining in current period"""
        if not self.is_current_period:
            return 0
        return (self.period_end - timezone.now()).days

    @property
    def performance_score(self):
        """Calculate budget performance score (0-100)"""
        if self.limit == 0:
            return 100
        
        usage_percentage = self.percentage_used
        
        if usage_percentage <= 80:
            return 100
        elif usage_percentage <= 100:
            return max(0, 100 - (usage_percentage - 80) * 5)
        else:
            return max(0, 50 - (usage_percentage - 100))

    def reset_spent(self):
        """Reset spent amount to zero"""
        self.spent = Decimal('0.00')
        self.save(update_fields=['spent', 'updated_at'])

    def advance_period(self):
        """Advance to next period and reset spent amount"""
        self.spent = Decimal('0.00')
        self.set_period_dates()
        self.save()


class BudgetHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='history')
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    spent = models.DecimalField(max_digits=12, decimal_places=2)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['budget', 'period_start']),
        ]

    def __str__(self):
        return f"{self.budget.category} - {self.period_start.strftime('%Y-%m')}"

    @property
    def percentage_used(self):
        if self.limit == 0:
            return 0
        return float((self.spent / self.limit) * 100)

    @property
    def remaining(self):
        return self.limit - self.spent


class BudgetAlert(models.Model):
    ALERT_TYPES = [
        ('threshold', 'Threshold Reached'),
        ('exceeded', 'Budget Exceeded'),
        ('period_end', 'Period Ending'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['budget', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.budget.category} - {self.get_alert_type_display()}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


class BudgetTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BudgetTemplateItem(models.Model):
    template = models.ForeignKey(BudgetTemplate, on_delete=models.CASCADE, related_name='items')
    category = models.CharField(max_length=100)
    limit = models.DecimalField(max_digits=12, decimal_places=2)
    period = models.CharField(max_length=20, choices=Budget.PERIOD_CHOICES, default='monthly')
    color = models.CharField(max_length=20, choices=Budget.COLOR_CHOICES, default='bg-blue-500')
    alert_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('80.00'))

    class Meta:
        unique_together = ['template', 'category']

    def __str__(self):
        return f"{self.template.name} - {self.category}"
