from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from datetime import datetime, timedelta


class SavingsAccount(models.Model):
    """
    Main savings account where automatic savings are deposited
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_account')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    auto_save_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage of income to automatically save"
    )
    is_auto_save_enabled = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'savings_account'
        verbose_name = 'Savings Account'
        verbose_name_plural = 'Savings Accounts'
    
    def __str__(self):
        return f"{self.user.username}'s Savings Account - KES {self.balance}"
    
    def add_funds(self, amount, description=""):
        """Add funds to savings account"""
        if amount > 0:
            old_balance = self.balance
            self.balance += Decimal(str(amount))
            self.save(update_fields=['balance', 'updated_at'])
            
            # Create transaction record
            SavingsTransaction.objects.create(
                savings_account=self,
                transaction_type='deposit',
                amount=amount,
                description=description or f"Deposit of KES {amount}",
                balance_before=old_balance,
                balance_after=self.balance
            )
    
    def withdraw_funds(self, amount, description=""):
        """Withdraw funds from savings account"""
        if amount > 0 and self.balance >= Decimal(str(amount)):
            old_balance = self.balance
            self.balance -= Decimal(str(amount))
            self.save(update_fields=['balance', 'updated_at'])
            
            # Create transaction record
            SavingsTransaction.objects.create(
                savings_account=self,
                transaction_type='withdrawal',
                amount=amount,
                description=description or f"Withdrawal of KES {amount}",
                balance_before=old_balance,
                balance_after=self.balance
            )
            return True
        return False
    
    def can_withdraw(self, amount):
        """Check if withdrawal amount is available"""
        return self.balance >= Decimal(str(amount))


class SavingsGoal(models.Model):
    """
    Individual savings goals (pots) that users can create
    """
    COLOR_CHOICES = [
        ('bg-red-500', 'Red'),
        ('bg-yellow-500', 'Yellow'),
        ('bg-indigo-500', 'Indigo'),
        ('bg-green-500', 'Green'),
        ('bg-purple-500', 'Purple'),
        ('bg-blue-500', 'Blue'),
        ('bg-pink-500', 'Pink'),
        ('bg-gray-500', 'Gray'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    target_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='bg-red-500')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Target date (optional)
    target_date = models.DateField(null=True, blank=True)
    
    # Auto-allocation settings
    auto_allocate_enabled = models.BooleanField(default=False)
    auto_allocate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Percentage of savings to auto-allocate to this goal"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'savings_goal'
        verbose_name = 'Savings Goal'
        verbose_name_plural = 'Savings Goals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['target_date']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach target"""
        return max(Decimal('0.00'), self.target_amount - self.current_amount)
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.target_amount == 0:
            return 100.0
        return min(100.0, float((self.current_amount / self.target_amount) * 100))
    
    @property
    def is_completed(self):
        """Check if goal is completed"""
        return self.current_amount >= self.target_amount
    
    @property
    def days_remaining(self):
        """Calculate days remaining to target date"""
        if not self.target_date:
            return None
        today = timezone.now().date()
        if self.target_date > today:
            return (self.target_date - today).days
        return 0
    
    @property
    def daily_saving_required(self):
        """Calculate daily saving amount required to meet target"""
        if not self.target_date or self.is_completed:
            return Decimal('0.00')
        
        days_remaining = self.days_remaining
        if days_remaining and days_remaining > 0:
            return self.remaining_amount / days_remaining
        return Decimal('0.00')
    
    def add_funds(self, amount, source='manual', description=""):
        """Add funds to this savings goal"""
        if amount > 0:
            old_amount = self.current_amount
            self.current_amount += Decimal(str(amount))
            
            # Check if goal is now completed
            if not self.completed_at and self.is_completed:
                self.status = 'completed'
                self.completed_at = timezone.now()
            
            self.save(update_fields=['current_amount', 'status', 'completed_at', 'updated_at'])
            
            # Create allocation record
            SavingsAllocation.objects.create(
                savings_goal=self,
                amount=amount,
                allocation_type='deposit',
                source=source,
                description=description or f"Added KES {amount} to {self.name}",
                balance_before=old_amount,
                balance_after=self.current_amount
            )
            
            return True
        return False
    
    def withdraw_funds(self, amount, description=""):
        """Withdraw funds from this savings goal"""
        if amount > 0 and self.current_amount >= Decimal(str(amount)):
            old_amount = self.current_amount
            self.current_amount -= Decimal(str(amount))
            
            # Update status if was completed but no longer
            if self.status == 'completed' and not self.is_completed:
                self.status = 'active'
                self.completed_at = None
            
            self.save(update_fields=['current_amount', 'status', 'completed_at', 'updated_at'])
            
            # Create allocation record
            SavingsAllocation.objects.create(
                savings_goal=self,
                amount=amount,
                allocation_type='withdrawal',
                source='manual',
                description=description or f"Withdrew KES {amount} from {self.name}",
                balance_before=old_amount,
                balance_after=self.current_amount
            )
            
            return True
        return False
    
    def can_withdraw(self, amount):
        """Check if withdrawal amount is available"""
        return self.current_amount >= Decimal(str(amount))


class SavingsTransaction(models.Model):
    """
    Transaction history for savings account
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('auto_save', 'Automatic Saving'),
        ('transfer', 'Transfer'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    savings_account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Reference to original transaction if auto-save
    reference_transaction_id = models.UUIDField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'savings_transaction'
        verbose_name = 'Savings Transaction'
        verbose_name_plural = 'Savings Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['savings_account', 'created_at']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - KES {self.amount}"


class SavingsAllocation(models.Model):
    """
    Track allocations to/from specific savings goals
    """
    ALLOCATION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('auto_allocation', 'Auto Allocation'),
        ('transfer', 'Transfer'),
    ]
    
    SOURCE_TYPES = [
        ('manual', 'Manual'),
        ('auto_save', 'Auto Save'),
        ('transfer', 'Transfer'),
        ('interest', 'Interest'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    savings_goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPES)
    source = models.CharField(max_length=20, choices=SOURCE_TYPES, default='manual')
    description = models.CharField(max_length=255)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'savings_allocation'
        verbose_name = 'Savings Allocation'
        verbose_name_plural = 'Savings Allocations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['savings_goal', 'created_at']),
            models.Index(fields=['allocation_type']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"{self.savings_goal.name} - {self.get_allocation_type_display()} - KES {self.amount}"


class SavingsTemplate(models.Model):
    """
    Pre-defined savings goal templates
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    suggested_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    suggested_timeline_months = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=20, choices=SavingsGoal.COLOR_CHOICES, default='bg-blue-500')
    priority = models.CharField(max_length=20, choices=SavingsGoal.PRIORITY_CHOICES, default='medium')
    is_default = models.BooleanField(default=False)
    category = models.CharField(max_length=100, default='general')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'savings_template'
        verbose_name = 'Savings Template'
        verbose_name_plural = 'Savings Templates'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class SavingsReport(models.Model):
    """
    Monthly/periodic savings reports
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_reports')
    report_date = models.DateField()
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Report data
    total_saved = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    auto_saved = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    manual_saved = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_savings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Goals data
    goals_completed = models.PositiveIntegerField(default=0)
    goals_in_progress = models.PositiveIntegerField(default=0)
    average_goal_progress = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'savings_report'
        verbose_name = 'Savings Report'
        verbose_name_plural = 'Savings Reports'
        ordering = ['-report_date']
        unique_together = ['user', 'report_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.report_date}"


class SavingsSettings(models.Model):
    """
    User-specific savings settings
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_settings')
    
    # Auto-save settings
    auto_save_enabled = models.BooleanField(default=True)
    auto_save_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Notification settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Reminder settings
    goal_reminders = models.BooleanField(default=True)
    monthly_reports = models.BooleanField(default=True)
    achievement_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'savings_settings'
        verbose_name = 'Savings Settings'
        verbose_name_plural = 'Savings Settings'
    
    def __str__(self):
        return f"{self.user.username}'s Savings Settings"
