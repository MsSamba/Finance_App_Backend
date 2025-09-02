from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

# class Category(models.Model):
#     """Transaction categories - simplified to match frontend"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=100, unique=True)
#     icon = models.CharField(max_length=10, default='💰')
#     is_income_category = models.BooleanField(default=False)  # True for Income category
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name_plural = "Categories"
#         ordering = ['name']
    
#     def __str__(self):
#         return f"{self.icon} {self.name}"

class Transaction(models.Model):
    """User transactions - simplified to match frontend"""
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.CharField(max_length=255)
    # category = models.CharField(max_length=100)  # Store category name as string like frontend
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)  # Match frontend field name
    date = models.DateField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'type']),
            # models.Index(fields=['user', 'category']),
        ]
    
    def __str__(self):
        sign = '+' if self.type == 'income' else '-'
        return f"{sign}KES {self.amount} - {self.description}"
    
    @property
    def signed_amount(self):
        """Return amount with proper sign based on transaction type"""
        return self.amount if self.type == 'income' else -self.amount